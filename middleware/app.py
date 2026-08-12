import os

import ollama
import psycopg
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")

# Failures here are dependency failures, not bugs: the database may not be up, or
# the model may never have been pulled. Both must return JSON with an actionable
# message. An unhandled exception returns Flask's HTML error page, the browser's
# res.json() then throws on the HTML, and the UI reports a *network* problem for
# what was actually a served response — sending the reader to debug ports and CORS
# that were fine all along.
PULL_HINT = (
    f"Model '{OLLAMA_MODEL}' is unavailable. Run: "
    f"docker compose exec middleware ollama pull {OLLAMA_MODEL}"
)


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
    try:
        return jsonify({"items": fetch_inventory()})
    except psycopg.Error as e:
        app.logger.error("database unavailable: %s", e)
        return jsonify({"error": "Database unavailable. Is the db container healthy?"}), 503


@app.route("/api/ask", methods=["POST"])
def ask():
    # A non-JSON body makes get_json() return None (or raise), so validate before
    # calling .get() on it — otherwise a malformed request is a 500, not a 400.
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "request body must be a JSON object"}), 400

    user_question = (data.get("message") or "").strip()
    if not user_question:
        return jsonify({"error": "message is required"}), 400

    try:
        items = fetch_inventory()
    except psycopg.Error as e:
        app.logger.error("database unavailable: %s", e)
        return jsonify({"error": "Database unavailable. Is the db container healthy?"}), 503

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

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question},
            ],
        )
    except ollama.ResponseError as e:
        # The overwhelmingly common cause is the one-time `ollama pull` never
        # having been run, so name the exact command rather than echoing the
        # library's error.
        app.logger.error("ollama request failed: %s", e)
        return jsonify({"error": PULL_HINT}), 503
    except Exception as e:  # ollama serve down, socket refused, timeout
        app.logger.error("ollama unreachable: %s", e)
        return jsonify({"error": "LLM service unreachable inside the container."}), 503

    return jsonify({"answer": response["message"]["content"]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
