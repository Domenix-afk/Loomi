"""Tests für die Web-App: LoomiApp (API-Schicht) und HTTP-End-to-End."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from webapp.app import LoomiApp
from webapp.server import create_server, resolve_bind


# --- Helfer ---


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


def make_wardrobe(app):
    app.add_item(make_item_payload(name="T-Shirt"))
    app.add_item(make_item_payload(name="Jeans", category="bottom"))


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


def request(method, url, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            raw = res.read().decode("utf-8")
            try:
                return res.status, json.loads(raw)
            except ValueError:
                return res.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(raw)
        except ValueError:
            return exc.code, raw


@pytest.fixture()
def server(tmp_path):
    app = LoomiApp(str(tmp_path / "loomi.db"))
    srv = create_server(app, "127.0.0.1", 0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    yield base
    srv.shutdown()
    srv.server_close()


# --- LoomiApp: Kleiderschrank ---


def test_add_list_delete(tmp_path):
    app = LoomiApp(str(tmp_path / "loomi.db"))
    item = app.add_item(make_item_payload())
    assert item["name"] == "Weißes T-Shirt"
    assert item["category"] == "top"
    assert app.list_items()["count"] == 1
    assert app.delete_item(item["id"]) == {"deleted": item["id"]}
    assert app.list_items()["count"] == 0


def test_add_item_validation(tmp_path):
    app = LoomiApp(str(tmp_path / "loomi.db"))
    with pytest.raises(ValueError):
        app.add_item(make_item_payload(name=""))
    with pytest.raises(ValueError):
        app.add_item(make_item_payload(category="hut"))
    with pytest.raises(ValueError):
        app.add_item(make_item_payload(color="kitschig"))
    with pytest.raises(ValueError):
        app.add_item(make_item_payload(warmth=9))
    with pytest.raises(ValueError):
        app.add_item(make_item_payload(formality="x"))


def test_delete_missing_item_raises(tmp_path):
    app = LoomiApp(str(tmp_path / "loomi.db"))
    with pytest.raises(KeyError):
        app.delete_item("gibt-es-nicht")


def test_sample_load_idempotent_and_remove_only_sample(tmp_path):
    app = LoomiApp(str(tmp_path / "loomi.db"))
    assert app.load_sample()["added"] == 32
    assert app.load_sample()["added"] == 0  # idempotent

    app.add_item(make_item_payload(name="Eigener Pullover"))
    assert app.remove_sample()["removed"] == 32
    assert app.list_items()["count"] == 1  # eigene Teile bleiben
    assert app.remove_sample()["removed"] == 0


# --- LoomiApp: Empfehlung ---


def test_recommend_uses_stored_wardrobe(tmp_path):
    app = LoomiApp(str(tmp_path / "loomi.db"))
    make_wardrobe(app)
    data = app.recommend(recommend_payload())
    assert data["wardrobe_count"] == 2
    assert len(data["outfits"]) == 1
    scored = data["outfits"][0]
    assert scored["total"] > 0
    assert {c["component"] for c in scored["components"]} == {
        "style", "color", "occasion", "weather", "variety", "preference",
    }
    assert [i["slot"] for i in scored["outfit"]["items"]] == ["top", "bottom"]
    assert data["context"]["condition"] == "sunny"


def test_recommend_echoes_context_and_style(tmp_path):
    app = LoomiApp(str(tmp_path / "loomi.db"))
    make_wardrobe(app)
    data = app.recommend(recommend_payload(temperature=10.0, condition="rain", occasion="work", preferred_style="business"))
    ctx = data["context"]
    assert ctx["temperature"] == 10.0
    assert ctx["condition"] == "rain"
    assert ctx["occasion"] == "work"
    assert ctx["preferred_style"] == "business"


def test_recommend_empty_wardrobe(tmp_path):
    app = LoomiApp(str(tmp_path / "loomi.db"))
    data = app.recommend(recommend_payload())
    assert data["outfits"] == []
    assert data["wardrobe_count"] == 0


def test_recommend_validation(tmp_path):
    app = LoomiApp(str(tmp_path / "loomi.db"))
    with pytest.raises(ValueError):
        app.recommend(recommend_payload(temperature=100))
    with pytest.raises(ValueError):
        app.recommend(recommend_payload(condition="blizzard"))
    with pytest.raises(ValueError):
        app.recommend(recommend_payload(preferred_style="royal"))


# --- LoomiApp: Feedback & Profil ---


def test_feedback_updates_and_persists_profile(tmp_path):
    db = str(tmp_path / "loomi.db")
    app = LoomiApp(db)
    make_wardrobe(app)
    rec = app.recommend(recommend_payload())
    scored = rec["outfits"][0]

    res = app.add_feedback({"rating": 5, "outfit": scored["outfit"], "context": rec["context"]})
    assert res["feedback_count"] == 1

    # Neue Sitzung (frisches App-Objekt) lädt das gespeicherte Profil
    app2 = LoomiApp(db)
    prefs = app2.preferences()
    assert prefs["feedback_count"] == 1
    assert prefs["values"]  # gelernte Attributwerte vorhanden
    assert prefs["numeric"]  # Wärme-/Formalitäts-Präferenz vorhanden


def test_feedback_validation(tmp_path):
    app = LoomiApp(str(tmp_path / "loomi.db"))
    make_wardrobe(app)
    scored = app.recommend(recommend_payload())["outfits"][0]

    with pytest.raises(ValueError):
        app.add_feedback({"rating": 9, "outfit": scored["outfit"]})
    with pytest.raises(ValueError):
        app.add_feedback({"rating": 3, "outfit": {"items": [{"id": "unbekannt"}]}})
    with pytest.raises(ValueError):
        app.add_feedback({"rating": 3})


def test_feedback_accepts_bare_items_list(tmp_path):
    """Regression: Das Frontend sendet `outfit` als Item-Liste (wie im Browser)."""
    app = LoomiApp(str(tmp_path / "loomi.db"))
    make_wardrobe(app)
    rec = app.recommend(recommend_payload())
    items = rec["outfits"][0]["outfit"]["items"]

    res = app.add_feedback({"rating": 5, "outfit": items, "context": rec["context"]})
    assert res["feedback_count"] == 1

    prefs = app.preferences()
    assert prefs["feedback_count"] == 1
    assert prefs["values"]


def test_preferences_reset(tmp_path):
    db = str(tmp_path / "loomi.db")
    app = LoomiApp(db)
    make_wardrobe(app)
    scored = app.recommend(recommend_payload())["outfits"][0]
    app.add_feedback({"rating": 4, "outfit": scored["outfit"]})
    assert app.preferences()["feedback_count"] == 1

    app.reset_preferences()
    assert app.preferences()["feedback_count"] == 0
    assert app.preferences()["values"] == []
    # Auch nach Neustart bleibt das Profil zurückgesetzt
    assert LoomiApp(db).preferences()["feedback_count"] == 0


# --- HTTP End-to-End: alle Endpunkte ---


# --- Bind-Adresse für Plattformen (Render/Heroku) ---


class _Args:
    def __init__(self, host=None, port=None):
        self.host = host
        self.port = port


def test_resolve_bind_local_defaults():
    assert resolve_bind(_Args(), environ={}) == ("127.0.0.1", 8000)


def test_resolve_bind_uses_port_env_for_platforms():
    assert resolve_bind(_Args(), environ={"PORT": "10000"}) == ("0.0.0.0", 10000)


def test_resolve_bind_cli_args_win_over_env():
    args = _Args(host="127.0.0.1", port=9000)
    assert resolve_bind(args, environ={"PORT": "10000"}) == ("127.0.0.1", 9000)


# --- HTTP End-to-End ---


def test_http_serves_frontend(server):
    status, body = request("GET", server + "/")
    assert status == 200
    assert "loomi" in body

    status, css = request("GET", server + "/static/style.css")
    assert status == 200 and "Loomi" in css

    status, js = request("GET", server + "/static/app.js")
    assert status == 200 and "runRecommend" in js


def test_http_full_user_flow(server):
    # 1. Kleiderschrank: eigene Teile anlegen
    status, item1 = request("POST", server + "/api/wardrobe/items",
                            make_item_payload(name="T-Shirt"))
    assert status == 201
    status, item2 = request("POST", server + "/api/wardrobe/items",
                            make_item_payload(name="Jeans", category="bottom"))
    assert status == 201

    # 2. Beispieldaten laden (idempotent)
    status, res = request("POST", server + "/api/wardrobe/sample")
    assert status == 200 and res["added"] == 32
    status, res = request("POST", server + "/api/wardrobe/sample")
    assert res["added"] == 0

    status, wardrobe = request("GET", server + "/api/wardrobe")
    assert status == 200 and wardrobe["count"] == 34

    # 3. Empfehlung
    status, rec = request("POST", server + "/api/recommend", recommend_payload())
    assert status == 200
    assert len(rec["outfits"]) == 3
    assert "preference" in {c["component"] for c in rec["outfits"][0]["components"]}

    # 4. Feedback auf das beste Outfit
    status, fb = request("POST", server + "/api/feedback", {
        "rating": 5, "outfit": rec["outfits"][0]["outfit"], "context": rec["context"],
    })
    assert status == 201 and fb["feedback_count"] == 1

    # 5. Profil zeigt die gelernte Präferenz
    status, prefs = request("GET", server + "/api/preferences")
    assert status == 200 and prefs["feedback_count"] == 1

    # 6. Profil zurücksetzen
    status, reset = request("DELETE", server + "/api/preferences")
    assert status == 200 and reset["feedback_count"] == 0

    # 7. Ein eigenes Kleidungsstück löschen, dann Beispieldaten entfernen
    status, deleted = request("DELETE", server + f"/api/wardrobe/items/{item1['id']}")
    assert status == 200 and deleted["deleted"] == item1["id"]

    status, removed = request("DELETE", server + "/api/wardrobe/sample")
    assert status == 200 and removed["removed"] == 32

    status, wardrobe = request("GET", server + "/api/wardrobe")
    assert status == 200 and wardrobe["count"] == 1  # nur noch Jeans


def test_http_feedback_matches_frontend_shape(server):
    """Regression: Feedback-POST exakt wie von app.js gesendet (Item-Liste)."""
    request("POST", server + "/api/wardrobe/items", make_item_payload(name="T-Shirt"))
    request("POST", server + "/api/wardrobe/items",
            make_item_payload(name="Jeans", category="bottom"))
    status, rec = request("POST", server + "/api/recommend", recommend_payload())
    assert status == 200

    items = rec["outfits"][0]["outfit"]["items"]  # [{slot, id, name, ...}, ...]
    status, fb = request("POST", server + "/api/feedback",
                         {"rating": 5, "outfit": items, "context": rec["context"]})
    assert status == 201 and fb["feedback_count"] == 1


def test_http_error_cases(server):
    status, body = request("POST", server + "/api/recommend",
                           recommend_payload(condition="blizzard"))
    assert status == 400 and "error" in body

    status, body = request("POST", server + "/api/wardrobe/items",
                           make_item_payload(warmth=99))
    assert status == 400

    status, body = request("POST", server + "/api/feedback",
                           {"rating": 3, "outfit": {"items": [{"id": "gibts-nicht"}]}})
    assert status == 400

    status, body = request("DELETE", server + "/api/wardrobe/items/gibts-nicht")
    assert status == 404

    status, body = request("GET", server + "/api/gibtesnicht")
    assert status == 404

    status, body = request("GET", server + "/static/gibtesnicht.css")
    assert status == 404


def test_http_delete_item_with_umlaut_id(server):
    # Browser senden IDs percent-encodiert (z. B. „Weißes-T-Shirt-…“)
    from urllib.parse import quote

    status, item = request("POST", server + "/api/wardrobe/items",
                           make_item_payload(name="Weißes T-Shirt"))
    assert status == 201

    status, deleted = request("DELETE", server + "/api/wardrobe/items/" + quote(item["id"]))
    assert status == 200 and deleted["deleted"] == item["id"]

    status, wardrobe = request("GET", server + "/api/wardrobe")
    assert status == 200 and wardrobe["count"] == 0
