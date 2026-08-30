"""Vercel-Adapter für die bestehende Loomi Web-App.

Dünne WSGI-Schicht (Standardbibliothek, keine Abhängigkeiten), die Request von
Vercel an die bereits vorhandene Funktionalität weiterleitet:

    Vercel  ->  wsgi.app  ->  webapp.server.route_api / LoomiApp  ->  Loomi-Kern

- `/api/*`  wird über `route_api` auf die bestehende `LoomiApp` gemappt
  (identisch zum lokalen `webapp.server`).
- `/` und `/static/*` bedienen die bestehenden Frontend-Dateien aus
  `webapp/static/`.

LoomiCore, LoomiApp und die API-Logik bleiben unangetastet – dieser Adapter
enthält keinerlei neue Funktionen, nur die Umgebungs-Anpassung für Vercels
Serverless/Request-Modell (WSGI-environ -> LoomiApp-Aufrufe).

Lokal testen (Vercel ruft intern dasselbe `app`-Objekt auf):
    python -c "from wsgiref.simple_server import make_server; from wsgi import app; make_server('127.0.0.1', 8000, app).serve_forever()"

Persistenz-Hinweis: Vercel-Funktionen haben ein ephemeres Dateisystem, daher
liegt die SQLite-Datenbank standardmäßig unter /tmp und überlebt Kaltstarts
nicht. Über die Umgebungsvariable LOOMI_DB_PATH kann auf eine verwaltete
Datenquelle (z. B. via SFTP-Mount oder externer DB) verwiesen werden.
"""

from __future__ import annotations

import json
import mimetypes
import os
from http import HTTPStatus

from webapp.app import LoomiApp
from webapp.server import STATIC_DIR, route_api

__all__ = ["app"]

# Lazy-Initialisierung (Vercel-Serverless): die App wird erst beim ersten
# Request aufgebaut. Der DB-Pfad kommt aus LOOMI_DB_PATH (Standard /tmp, weil
# das Dateisystem auf Vercel ephemer ist).
_loomi: LoomiApp | None = None


def _get_app() -> LoomiApp:
    global _loomi
    if _loomi is None:
        _loomi = LoomiApp(os.environ.get("LOOMI_DB_PATH", "/tmp/loomi.db"))
    return _loomi


def _read_static(rel_path: str) -> bytes | None:
    full = os.path.realpath(os.path.join(STATIC_DIR, rel_path))
    if not full.startswith(os.path.realpath(STATIC_DIR)) or not os.path.isfile(full):
        return None
    with open(full, "rb") as fh:
        return fh.read()


def _parse_body(environ) -> dict:
    try:
        length = int(environ.get("CONTENT_LENGTH") or "0")
    except (ValueError, TypeError):
        length = 0
    if length <= 0:
        return {}
    raw = environ["wsgi.input"].read(length)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise ValueError("Ungültiger JSON-Body") from None
    return data if isinstance(data, dict) else {}


def _json_response(payload) -> tuple[int, bytes, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return 200, body, "application/json; charset=utf-8"


def app(environ, start_response):
    """WSGI-Einstiegspunkt für Vercel (identische Routen wie webapp.server)."""
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/") or "/"

    try:
        if path.startswith("/api/"):
            status, payload = route_api(
                _get_app(),
                method,
                path,
                read_body=lambda: _parse_body(environ),
            )
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            content_type = "application/json; charset=utf-8"
        elif method == "GET" and path in ("/", "/index.html"):
            data = _read_static("index.html")
            if data is None:
                status, body, content_type = 404, b"Not Found", "text/plain; charset=utf-8"
            else:
                status, body, content_type = 200, data, "text/html; charset=utf-8"
        elif method == "GET" and path.startswith("/static/"):
            rel_path = path[len("/static/"):]
            data = _read_static(rel_path)
            if data is None:
                status, body, content_type = 404, b"Not Found", "text/plain; charset=utf-8"
            else:
                content_type = mimetypes.guess_type(rel_path)[0] or "application/octet-stream"
                status, body, content_type = 200, data, content_type
        elif method == "GET":
            # Unbekannte GET-Route (deckt auch die API-Nicht-Treffer ab).
            status, body, content_type = 404, b"Not Found", "text/plain; charset=utf-8"
        else:
            status, body, content_type = 405, b"Method Not Allowed", "text/plain; charset=utf-8"
    except KeyError as exc:
        status, body, content_type = _json_response({"error": str(exc)})
        status = 404
    except ValueError as exc:
        status, body, content_type = _json_response({"error": str(exc)})
        status = 400
    except Exception as exc:  # pragma: no cover – letzter Sicherheitsnetz
        status, body, content_type = _json_response({"error": f"Interner Fehler: {exc}"})
        status = 500

    reason = HTTPStatus(status).phrase
    start_response(
        f"{status} {reason}",
        [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]