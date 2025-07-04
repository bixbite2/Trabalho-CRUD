from flask import Flask, request, jsonify, render_template
import psycopg2
from datetime import date

app = Flask(__name__)

conn = psycopg2.connect(
    dbname="banco_prisco_distros",
    user="postgres",
    password="",
    host="localhost"
)

@app.route("/")
def index():
    return render_template("index.html")

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
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO distros (nome, data_adicionada, numero_de_usuarios, nota_media) VALUES (%s, %s, %s, %s) RETURNING id",
        (nome, date.today(), 0, 0)
    )
    id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    return jsonify({"id": id})

@app.route("/usuario", methods=["POST"])
def usuario():
    nome = request.json["nome"]
    cur = conn.cursor()
    cur.execute("SELECT id FROM usuarios WHERE nome = %s", (nome,))
    row = cur.fetchone()
    if row:
        id = row[0]
    else:
        cur.execute("INSERT INTO usuarios (nome) VALUES (%s) RETURNING id", (nome,))
        id = cur.fetchone()[0]
        conn.commit()
    cur.close()
    return jsonify({"id": id})

@app.route("/avaliar", methods=["POST"])
def avaliar():
    d = request.json
    cur = conn.cursor()
    cur.execute("INSERT INTO avaliacoes (usuario_id, distro_id, nota) VALUES (%s, %s, %s)",
                (d["usuario_id"], d["distro_id"], d["nota"]))
    conn.commit()
    cur.execute("UPDATE distros SET numero_de_usuarios = numero_de_usuarios + 1 WHERE id = %s",
                (d["distro_id"],))
    cur.execute("SELECT AVG(nota) FROM avaliacoes WHERE distro_id = %s", (d["distro_id"],))
    media = cur.fetchone()[0]
    cur.execute("UPDATE distros SET nota_media = %s WHERE id = %s", (media, d["distro_id"]))
    conn.commit()
    cur.close()
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True)
