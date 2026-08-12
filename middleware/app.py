import os

import ollama
import psycopg
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")


def db_conn():
    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def fetch_inventory():
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, sku, name, quantity, unit_price "
            "FROM inventory ORDER BY id"
        )
        rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "sku": r[1],
            "name": r[2],
            "quantity": r[3],
            "unit_price": float(r[4]),
        }
        for r in rows
    ]


@app.route("/api/message", methods=["POST"])
def message():
    data = request.get_json()
    user_text = data.get("message", "")
    return jsonify({"reply": f"Middleware received: {user_text}"})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/inventory", methods=["GET"])
def list_inventory():
    return jsonify({"items": fetch_inventory()})


@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.get_json()
    user_question = (data.get("message") or "").strip()
    if not user_question:
        return jsonify({"error": "message is required"}), 400

    items = fetch_inventory()
    inventory_lines = "\n".join(
        f"- {it['sku']}: {it['name']}, qty={it['quantity']}, "
        f"unit_price=${it['unit_price']:.2f}"
        for it in items
    )
    system_prompt = (
        "You are an assistant for a small inventory system. "
        "Answer the user's question using only the inventory data below. "
        "Be concise. If the answer is not in the data, say so.\n\n"
        f"Current inventory:\n{inventory_lines}"
    )

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question},
        ],
    )
    return jsonify({"answer": response["message"]["content"]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
