"""Test panel for the three services – Team 4.

Serves the shop (/) and the test panel (/panel), and forwards requests
to the services from Python, so the browser never hits CORS problems.

Run from the matchday-microservices folder (standard library only, nothing to install):
    python front/servidor.py
Then open http://localhost:8080 (shop) or http://localhost:8080/panel

If a service runs on another computer, pass its address, e.g.:
    DATA_URL=http://10.0.4.50:8001 python front/servidor.py
(variables: PUERTA_URL, DATA_URL, DECISION_URL)
"""

import json
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8080
TIMEOUT_SECONDS = 3
HERE = Path(__file__).parent
PAGES = {"/": "tienda.html", "/tienda": "tienda.html", "/panel": "panel.html"}

# Only these targets can be reached, so the panel is not an open proxy
SERVICES = {
    "datos": {"name": "Datos", "port": 8001, "health": "/equipaciones",
              "url": os.environ.get("DATA_URL", "http://localhost:8001")},
    "decision": {"name": "Decisión", "port": 8002, "health": "/salud",
                 "url": os.environ.get("DECISION_URL", "http://localhost:8002")},
    # Puerta has no /salud: a 401 without key also proves it is alive
    "puerta": {"name": "Puerta", "port": 8000, "health": "/pedidos",
               "url": os.environ.get("PUERTA_URL", "http://localhost:8000")},
}
ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def call_service(service, method, path, body=None, headers=None):
    """Make one request and describe the result. Never raises."""
    url = SERVICES[service]["url"].rstrip("/") + path
    data = None
    request_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode()
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=request_headers)

    start = time.perf_counter()
    instance_id = None
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            status, raw = response.status, response.read()
            instance_id = response.headers.get("X-Service-Instance")
    except urllib.error.HTTPError as error:  # 4xx / 5xx: the service answered
        status, raw = error.code, error.read()
        instance_id = error.headers.get("X-Service-Instance")
    except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
        reason = getattr(error, "reason", error)
        return {
            "url": url,
            "codigo": None,
            "ms": round((time.perf_counter() - start) * 1000),
            "error": f"No responde ({reason})",
        }

    text = raw.decode(errors="replace")
    try:
        payload = json.loads(text) if text else None
    except ValueError:
        payload = text[:2000]
    return {
        "url": url,
        "codigo": status,
        "ms": round((time.perf_counter() - start) * 1000),
        "cuerpo": payload,
        "instancia": instance_id,
    }


class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload, status=200):
        raw = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path in PAGES:
            raw = (HERE / PAGES[self.path]).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        elif self.path == "/api/estado":
            status = {}
            for key, service in SERVICES.items():
                result = call_service(key, "GET", service["health"])
                status[key] = {**result, "nombre": service["name"], "puerto": service["port"]}
            self.send_json(status)
        else:
            self.send_json({"detail": "No existe"}, 404)

    def do_POST(self):
        if self.path not in {"/api/probar", "/api/limite"}:
            self.send_json({"detail": "No existe"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            order = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/limite":
                api_key = order["api_key"]
                if not isinstance(api_key, str) or not api_key:
                    raise ValueError
                self.send_json(call_service(
                    "puerta", "GET", "/limite", headers={"X-API-Key": api_key},
                ))
                return

            service = order["servicio"]
            method = order.get("metodo", "GET").upper()
            path = order.get("ruta", "/")
            if service not in SERVICES or method not in ALLOWED_METHODS or not path.startswith("/"):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            self.send_json({"detail": "Petición de prueba mal formada"}, 400)
            return
        self.send_json(call_service(service, method, path, order.get("cuerpo"), order.get("cabeceras")))

    def log_message(self, *args):  # keep the terminal quiet
        pass


if __name__ == "__main__":
    for service in SERVICES.values():
        print(f"  {service['name']:9} → {service['url']}")
    print(f"Tienda en http://localhost:{PORT}  ·  panel de pruebas en http://localhost:{PORT}/panel  (Ctrl+C para salir)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
