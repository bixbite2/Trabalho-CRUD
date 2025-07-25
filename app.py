from functools import wraps
from flask import Flask, render_template_string, request, jsonify, render_template, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from datetime import date
import secrets
import string

app = Flask(__name__)
app.secret_key = "I|6C!lISAO[$3KU8fO7vC`~WogVNcJUiJYE`p8MU0j|KVeW#?Heqs7'U|L0T8~7-'"

conn = psycopg2.connect(
    dbname="banco_prisco_distros",
    user="postgres",
    password="",
    host="localhost"
)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('main'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('main'))
        
        cur = conn.cursor()
        cur.execute("SELECT username FROM usuarios WHERE id = %s", (session['user_id'],))
        user = cur.fetchone()
        cur.close()

        if user and user[0] == 'bixbite':
            return f(*args, **kwargs)
        else:
            flash('You do not have permission to access this page.')
            return redirect(url_for('user'))
    return decorated_function

# Páginas

@app.route("/", methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        cur = conn.cursor()
        cur.execute("SELECT id, senha_hash FROM usuarios WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            if username == 'bixbite':
                return redirect(url_for('admin'))
            return redirect(url_for('user'))
        else:
            flash('Invalid username or password')

    return render_template("main.html")

@app.route("/admin")
@admin_required
def admin():
    return render_template("admin.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm-password')

        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match!")

        cur = conn.cursor()
        cur.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
        if cur.fetchone():
            cur.close()
            return render_template("register.html", error="Username already exists!")

        # Hash the password for security
        password_hash = generate_password_hash(password)

        cur.execute("INSERT INTO usuarios (username, senha_hash) VALUES (%s, %s)", (username, password_hash))
        conn.commit()
        cur.close()

        return redirect(url_for('main')) # Redirect to login page after successful registration

    return render_template("register.html")


# Rotas para as distros

@app.route("/distros")
def distros():
    cur = conn.cursor()
    cur.execute("SELECT * FROM distros")
    data = cur.fetchall()
    cur.close()
    return jsonify(data)

@app.route("/nova_distro", methods=["POST"])
def nova_distro():
    nome = request.json["nome"]
    baseada_em = request.json.get("baseada_em")  # Use .get for optional fields
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO distros (nome, baseada_em, data_adicionada, numero_de_usuarios, nota_media) VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (nome, baseada_em, date.today(), 0, 0)
    )
    id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    return jsonify({"id": id})

@app.route("/user")
@login_required
def user():
    return render_template("index.html")

@app.route("/avaliar", methods=["POST"])
@login_required
def avaliar():
    d = request.json
    usuario_id = session['user_id']
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO avaliacoes (usuario_id, distro_id, nota) VALUES (%s, %s, %s)",
                    (usuario_id, d["distro_id"], d["nota"]))
        conn.commit()
        cur.execute("UPDATE distros SET numero_de_usuarios = numero_de_usuarios + 1 WHERE id = %s",
                    (d["distro_id"],))
        cur.execute("SELECT AVG(nota) FROM avaliacoes WHERE distro_id = %s", (d["distro_id"],))
        media = cur.fetchone()[0]
        cur.execute("UPDATE distros SET nota_media = %s WHERE id = %s", (media, d["distro_id"]))
        conn.commit()
        cur.close()
        return jsonify({"status": "ok"})
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        cur.close()
        return jsonify({"status": "error", "message": "Você já avaliou esta distro."}), 409
    except Exception as e:
        conn.rollback()
        cur.close()
        return jsonify({"status": "error", "message": str(e)}), 500

# Rotas para registro

@app.route("/remove_distro/<int:id>", methods=["DELETE"])
def remove_distro(id):
    cur = conn.cursor()
    try:
        # Primeiro, deleta as avaliações que fazem referência à distro
        cur.execute("DELETE FROM avaliacoes WHERE distro_id = %s", (id,))
        # Depois, deleta a distro
        cur.execute("DELETE FROM distros WHERE id = %s", (id,))
        conn.commit()
    except Exception as e:
        conn.rollback()  # Desfaz a transação em caso de erro
        print(f"Erro ao deletar distro: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cur.close()
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True)
