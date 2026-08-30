"""Tests für den Vercel-WSGI-Adapter (wsgi.py).

Der Adapter leitet alle Requests an die bestehende Loomi-Funktionalität
(`webapp.server.route_api` -> `LoomiApp`) weiter. Diese Tests treiben die
WSGI-`app` direkt (ohne HTTP-Server, wie Vercel sie intern aufruft) und
verifizieren, dass jeder Endpunkt und das Frontend funktionieren.
"""

import io
import json
import os

import pytest

import wsgi


# --- WSGI-Helfer (environ so, wie Vercel ihn bereitstellt) ---


def call_wsgi(path, method="GET", payload=None):
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "SERVER_NAME": "loomi.vercel.app",
        "SERVER_PORT": "443",
        "wsgi.url_scheme": "https",
        "wsgi.input": io.BytesIO(),
        "CONTENT_LENGTH": "0",
    }
    if payload is not None:
        raw = json.dumps(payload).encode("utf-8")
        environ["wsgi.input"] = io.BytesIO(raw)
        environ["CONTENT_LENGTH"] = str(len(raw))

    captured = {}

    def start_response(status, headers):
        # WSGI verlangt eine vollständige Statuszeile wie "200 OK"
        # (mindestens 4 Zeichen mit Reason Phrase) – genauso validieren auch
        # echte WSGI-Server (u. a. Vercel) den Aufruf.
        assert len(status) >= 4 and " " in status
        captured["status"] = status
        captured["headers"] = dict(headers)

    body = b"".join(wsgi.app(environ, start_response))
    captured["body"] = body
    captured["status_code"] = int(captured["status"].split()[0])
    return captured


def make_item_payload(name="Weißes T-Shirt", **overrides):
    payload = {
        "name": name,
        "category": "top",
        "color": "neutral",
        "style": "casual",
        "warmth": 1,
        "formality": 1,
    }
    payload.update(overrides)
    return payload


def recommend_payload(**overrides):
    payload = {
        "temperature": 20.0,
        "condition": "sunny",
        "occasion": "casual",
        "preferred_style": None,
        "top_k": 3,
    }
    payload.update(overrides)
    return payload


@pytest.fixture()
def vercel_app(tmp_path, monkeypatch):
    # Isolierte Datenbank pro Test + frischer LoomiApp-Zustand im Adapter.
    monkeypatch.setenv("LOOMI_DB_PATH", str(tmp_path / "loomi.db"))
    wsgi._loomi = None
    yield wsgi.app
    wsgi._loomi = None


# --- Frontend ---


def test_serves_index(vercel_app):
    res = call_wsgi("/")
    assert res["status_code"] == 200
    assert "Loomi" in res["body"].decode("utf-8")

    res = call_wsgi("/index.html")
    assert res["status_code"] == 200
    res = call_wsgi("/static/style.css")
    assert res["status_code"] == 200 and "Loomi" in res["body"].decode("utf-8")
    res = call_wsgi("/static/app.js")
    assert res["status_code"] == 200 and "runRecommend" in res["body"].decode("utf-8")


def test_serves_404_for_missing_static(vercel_app):
    res = call_wsgi("/static/gibtesnicht.css")
    assert res["status_code"] == 404
    res = call_wsgi("/gibtesnicht")
    assert res["status_code"] == 404


# --- API-Endpunkte (weitergeleitet an die bestehende LoomiApp) ---


def test_full_user_flow(vercel_app):
    # Kleiderschrank: eigene Teile anlegen
    res = call_wsgi("/api/wardrobe/items", "POST", make_item_payload(name="T-Shirt"))
    assert res["status_code"] == 201
    item1 = json.loads(res["body"])
    assert item1["category"] == "top"

    res = call_wsgi("/api/wardrobe/items", "POST",
                    make_item_payload(name="Jeans", category="bottom"))
    assert res["status_code"] == 201

    # Beispieldaten laden (idempotent)
    res = call_wsgi("/api/wardrobe/sample", "POST")
    assert res["status_code"] == 200 and json.loads(res["body"])["added"] == 32

    res = call_wsgi("/api/wardrobe")
    assert res["status_code"] == 200
    assert json.loads(res["body"])["count"] == 34

    # Empfehlung
    res = call_wsgi("/api/recommend", "POST", recommend_payload())
    assert res["status_code"] == 200
    rec = json.loads(res["body"])
    assert len(rec["outfits"]) == 3
    assert "preference" in {c["component"] for c in rec["outfits"][0]["components"]}

    # Feedback auf das beste Outfit (exakt wie vom Frontend gesendet: Item-Liste)
    items = rec["outfits"][0]["outfit"]["items"]
    res = call_wsgi("/api/feedback", "POST",
                    {"rating": 5, "outfit": items, "context": rec["context"]})
    assert res["status_code"] == 201
    assert json.loads(res["body"])["feedback_count"] == 1

    # Profil zeigt die gelernte Präferenz
    res = call_wsgi("/api/preferences")
    assert res["status_code"] == 200
    assert json.loads(res["body"])["feedback_count"] == 1

    # Profil zurücksetzen
    res = call_wsgi("/api/preferences", "DELETE")
    assert res["status_code"] == 200 and json.loads(res["body"])["feedback_count"] == 0

    # eigenes Teil Löschen (Umlaut-bewusst), dann Beispieldaten entfernen
    res = call_wsgi(f"/api/wardrobe/items/{item1['id']}", "DELETE")
    assert res["status_code"] == 200

    res = call_wsgi("/api/wardrobe/sample", "DELETE")
    assert res["status_code"] == 200
    removed = json.loads(res["body"])["removed"]
    assert removed == 32

    res = call_wsgi("/api/wardrobe")
    assert json.loads(res["body"])["count"] == 1  # nur noch Jeans


def test_api_error_cases(vercel_app):
    res = call_wsgi("/api/recommend", "POST", recommend_payload(temperature=100))
    assert res["status_code"] == 400 and "error" in json.loads(res["body"])

    res = call_wsgi("/api/wardrobe/items", "POST", make_item_payload(warmth=99))
    assert res["status_code"] == 400

    res = call_wsgi("/api/feedback", "POST",
                    {"rating": 3, "outfit": {"items": [{"id": "gibts-nicht"}]}})
    assert res["status_code"] == 400

    # unbekanntes Kleidungsstück -> KeyError -> 404
    res = call_wsgi("/api/wardrobe/items/gibts-nicht", "DELETE")
    assert res["status_code"] == 404

    # unbekannter Endpunkt -> 404
    res = call_wsgi("/api/gibtesnicht")
    assert res["status_code"] == 404

    # ungültiges JSON
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/api/recommend",
        "QUERY_STRING": "",
        "wsgi.input": io.BytesIO(b"{kaputt"),
        "CONTENT_LENGTH": str(len(b"{kaputt")),
    }
    captured = {}

    def start_response(status, headers):
        captured["status"] = status

    wsgi.app(environ, start_response)
    assert captured["status"].split()[0] == "400"