"""Tests for the middleware API.

Every dependency is mocked: no database, no LLM, no network. The point of most of
these is the failure paths — a dependency being down must produce JSON with an
actionable message and a 503, never Flask's HTML error page. An HTML body makes
the browser's res.json() throw, and the UI then reports a network problem for a
request that was served, sending the reader off to debug ports and CORS.

These live under middleware/ rather than at the repo root because the compose
build context is ./middleware — a root-level tests/ directory could not be copied
into the image at all.

Run inside the container (canonical — exercises the real dependency versions):
    docker compose exec middleware python -m unittest discover -s tests

Or from the repo root, if you have the middleware requirements installed:
    python -m unittest discover -s middleware/tests
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg  # noqa: E402
import ollama  # noqa: E402

import app as middleware  # noqa: E402

SAMPLE_ITEMS = [
    {"id": 1, "sku": "WID-1", "name": "Widget", "quantity": 4, "unit_price": 9.5},
    {"id": 2, "sku": "GIZ-2", "name": "Gizmo", "quantity": 0, "unit_price": 21.0},
]


class ApiCase(unittest.TestCase):
    def setUp(self):
        middleware.app.config["TESTING"] = True
        self.client = middleware.app.test_client()

    def post_ask(self, payload):
        return self.client.post("/api/ask", json=payload)


class TestHealth(ApiCase):
    def test_health_is_ok(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {"status": "ok"})


class TestInventory(ApiCase):
    def test_happy_path_returns_items(self):
        with mock.patch.object(middleware, "fetch_inventory", return_value=SAMPLE_ITEMS):
            r = self.client.get("/api/inventory")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["items"], SAMPLE_ITEMS)

    def test_database_down_returns_503_json_not_html(self):
        with mock.patch.object(middleware, "fetch_inventory",
                               side_effect=psycopg.OperationalError("refused")):
            r = self.client.get("/api/inventory")
        self.assertEqual(r.status_code, 503)
        self.assertIn("Database unavailable", r.get_json()["error"])
        self.assertEqual(r.mimetype, "application/json")


class TestAskValidation(ApiCase):
    def test_missing_message_is_rejected(self):
        r = self.post_ask({})
        self.assertEqual(r.status_code, 400)
        self.assertIn("required", r.get_json()["error"])

    def test_blank_message_is_rejected(self):
        r = self.post_ask({"message": "   "})
        self.assertEqual(r.status_code, 400)

    def test_non_object_json_body_is_a_400_not_a_500(self):
        r = self.client.post("/api/ask", json=["not", "an", "object"])
        self.assertEqual(r.status_code, 400)
        self.assertIn("JSON object", r.get_json()["error"])

    def test_non_json_body_is_a_400_not_a_500(self):
        r = self.client.post("/api/ask", data="plain text",
                             content_type="text/plain")
        self.assertEqual(r.status_code, 400)


class TestAskHappyPath(ApiCase):
    def test_returns_the_model_answer(self):
        reply = {"message": {"content": "Gizmo, with zero in stock."}}
        with mock.patch.object(middleware, "fetch_inventory", return_value=SAMPLE_ITEMS), \
             mock.patch.object(middleware.ollama, "chat", return_value=reply):
            r = self.post_ask({"message": "which item is out of stock?"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["answer"], "Gizmo, with zero in stock.")

    def test_inventory_is_injected_into_the_system_prompt(self):
        """The RAG contract: the model must be given the rows, not asked to guess."""
        reply = {"message": {"content": "ok"}}
        with mock.patch.object(middleware, "fetch_inventory", return_value=SAMPLE_ITEMS), \
             mock.patch.object(middleware.ollama, "chat", return_value=reply) as chat:
            self.post_ask({"message": "anything"})
        messages = chat.call_args.kwargs["messages"]
        system = next(m["content"] for m in messages if m["role"] == "system")
        self.assertIn("WID-1", system)
        self.assertIn("Gizmo", system)
        self.assertIn("qty=0", system)
        user = next(m["content"] for m in messages if m["role"] == "user")
        self.assertEqual(user, "anything")


class TestAskFailurePaths(ApiCase):
    def test_missing_model_names_the_pull_command(self):
        with mock.patch.object(middleware, "fetch_inventory", return_value=SAMPLE_ITEMS), \
             mock.patch.object(middleware.ollama, "chat",
                               side_effect=ollama.ResponseError("model not found")):
            r = self.post_ask({"message": "hello"})
        self.assertEqual(r.status_code, 503)
        error = r.get_json()["error"]
        self.assertIn("ollama pull", error)
        self.assertEqual(r.mimetype, "application/json")

    def test_llm_unreachable_is_503_json(self):
        with mock.patch.object(middleware, "fetch_inventory", return_value=SAMPLE_ITEMS), \
             mock.patch.object(middleware.ollama, "chat",
                               side_effect=ConnectionError("refused")):
            r = self.post_ask({"message": "hello"})
        self.assertEqual(r.status_code, 503)
        self.assertIn("unreachable", r.get_json()["error"])

    def test_database_down_during_ask_is_503_json(self):
        with mock.patch.object(middleware, "fetch_inventory",
                               side_effect=psycopg.OperationalError("refused")):
            r = self.post_ask({"message": "hello"})
        self.assertEqual(r.status_code, 503)
        self.assertIn("Database unavailable", r.get_json()["error"])

    def test_no_failure_path_returns_html(self):
        """Regression: every handled failure must stay JSON.

        An HTML error body is what made the UI report 'could not reach middleware'
        for a request the middleware had answered.
        """
        cases = [
            (psycopg.OperationalError("down"), None),
            (None, ollama.ResponseError("missing")),
            (None, ConnectionError("refused")),
        ]
        for db_exc, llm_exc in cases:
            with self.subTest(db=db_exc, llm=llm_exc):
                fetch = (mock.patch.object(middleware, "fetch_inventory", side_effect=db_exc)
                         if db_exc else
                         mock.patch.object(middleware, "fetch_inventory",
                                           return_value=SAMPLE_ITEMS))
                chat = (mock.patch.object(middleware.ollama, "chat", side_effect=llm_exc)
                        if llm_exc else
                        mock.patch.object(middleware.ollama, "chat",
                                          return_value={"message": {"content": "x"}}))
                with fetch, chat:
                    r = self.post_ask({"message": "hello"})
                self.assertEqual(r.mimetype, "application/json")


if __name__ == "__main__":
    unittest.main()
