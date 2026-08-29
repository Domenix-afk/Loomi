"""Web-Server für Loomi (nur Standardbibliothek).

Bedient die statische Frontend-Dateien aus `webapp/static` und eine
JSON-API, die ausschließlich die bestehenden Loomi-Funktionen nutzt.

Starten:
    python -m webapp.server                # http://127.0.0.1:8000
    python -m webapp.server --db pfad --port 8080
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from .app import LoomiApp

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# Ausgelieferte Dateien einmalig im Speicher halten (klein, statisch).
_STATIC_CACHE: dict[str, bytes] = {}


def _read_static(rel_path: str) -> bytes | None:
    if rel_path in _STATIC_CACHE:
        return _STATIC_CACHE[rel_path]
    full = os.path.realpath(os.path.join(STATIC_DIR, rel_path))
    if not full.startswith(os.path.realpath(STATIC_DIR)) or not os.path.isfile(full):
        return None
    with open(full, "rb") as fh:
        data = fh.read()
    _STATIC_CACHE[rel_path] = data
    return data


class LoomiHandler(BaseHTTPRequestHandler):
    """Bedient API-Routen und statische Dateien."""

    app: LoomiApp  # vom Server gesetzt

    # --- Helfer ---

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _error(self, status: int, message: str) -> None:
        self._json(status, {"error": message})

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ValueError("Ungültiger JSON-Body") from None
        return data if isinstance(data, dict) else {}

    def _route_api(self, method: str, path: str) -> None:
        app = self.app
        if method == "GET" and path == "/api/wardrobe":
            self._json(200, app.list_items())
        elif method == "POST" and path == "/api/wardrobe/items":
            self._json(201, app.add_item(self._read_body()))
        elif method == "DELETE" and path.startswith("/api/wardrobe/items/"):
            # Browser senden IDs percent-encodiert (z. B. bei Umlauten).
            item_id = unquote(path[len("/api/wardrobe/items/"):])
            self._json(200, app.delete_item(item_id))
        elif method == "POST" and path == "/api/wardrobe/sample":
            self._json(200, app.load_sample())
        elif method == "DELETE" and path == "/api/wardrobe/sample":
            self._json(200, app.remove_sample())
        elif method == "POST" and path == "/api/recommend":
            self._json(200, app.recommend(self._read_body()))
        elif method == "POST" and path == "/api/feedback":
            self._json(201, app.add_feedback(self._read_body()))
        elif method == "GET" and path == "/api/preferences":
            self._json(200, app.preferences())
        elif method == "DELETE" and path == "/api/preferences":
            self._json(200, app.reset_preferences())
        else:
            self._error(404, f"Unbekannter Endpunkt: {method} {path}")

    # --- Standard-Methoden ---

    def _handle(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path.startswith("/api/"):
                self._route_api(method, path)
            elif method == "GET":
                if path == "/" or path == "/index.html":
                    self._serve_static("index.html", "text/html; charset=utf-8")
                elif path.startswith("/static/"):
                    self._serve_static(path[len("/static/"):])
                else:
                    self._error(404, "Nicht gefunden")
            else:
                self._error(405, "Methode nicht erlaubt")
        except KeyError as exc:
            self._error(404, str(exc))
        except ValueError as exc:
            self._error(400, str(exc))
        except Exception as exc:  # pragma: no cover – letzter Sicherheitsnetz
            self._error(500, f"Interner Fehler: {exc}")

    def _serve_static(self, rel_path: str, content_type: str | None = None) -> None:
        data = _read_static(rel_path)
        if data is None:
            self._error(404, "Nicht gefunden")
            return
        if content_type is None:
            import mimetypes

            content_type = mimetypes.guess_type(rel_path)[0] or "application/octet-stream"
        self._send(200, data, content_type)

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_DELETE(self) -> None:
        self._handle("DELETE")

    def log_message(self, format: str, *args) -> None:
        pass  # ruhige Konsole; Start-URL wird separat ausgegeben


def create_server(app: LoomiApp, host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    """Baut einen Server um eine LoomiApp (für Tests auf Port 0 möglich)."""
    handler = type("BoundLoomiHandler", (LoomiHandler,), {"app": app})
    return ThreadingHTTPServer((host, port), handler)


def resolve_bind(args, environ: dict | None = None) -> tuple[str, int]:
    """Bestimmt Host/Port: CLI-Argumente gewinnen, sonst PORT/HOST aus der Umgebung.

    Render (und ähnliche Plattformen) setzen die Umgebungsvariable `PORT`
    und erwarten, dass die App auf `0.0.0.0` lauscht. Lokal (ohne `PORT`)
    bleibt es bei 127.0.0.1:8000.
    """
    environ = environ if environ is not None else os.environ
    port = args.port if args.port is not None else int(environ.get("PORT", "8000"))
    host = args.host
    if host is None:
        host = "0.0.0.0" if environ.get("PORT") else "127.0.0.1"
    return host, port


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description="Loomi Web-App (bestehender Loomi-Kern)")
    parser.add_argument("--host", default=None, help="Bind-Adresse (Standard: 127.0.0.1 bzw. 0.0.0.0 mit PORT)")
    parser.add_argument("--port", type=int, default=None, help="Port (Standard: 8000 bzw. $PORT)")
    parser.add_argument("--db", default="loomi.db", help="Pfad zur SQLite-Datenbank")
    parser.add_argument("--open", action="store_true", help="Browser automatisch öffnen")
    args = parser.parse_args()

    host, port = resolve_bind(args)
    app = LoomiApp(args.db)
    server = create_server(app, host, port)
    url = f"http://{host}:{server.server_address[1]}"
    print(f"Loomi Web-App läuft unter {url}  (Datenbank: {args.db})")
    print("Beenden mit Strg+C")
    if args.open:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBis bald!")
        server.server_close()


if __name__ == "__main__":
    main()
