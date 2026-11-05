"""Flask gateway for the equipment shop (port 8000)."""

from collections import deque
from math import isfinite
import hmac
import os
import re
from threading import Lock
from time import monotonic
from uuid import uuid4

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["API_KEY"] = os.environ.get("API_KEY")
SERVICE_INSTANCE_ID = uuid4().hex

DECISION_URL = os.environ.get("DECISION_URL", "http://localhost:8002")
DATA_URL = os.environ.get("DATA_URL", "http://localhost:8001")
TIMEOUT_SECONDS = 3
MAX_REQUESTS_PER_MINUTE = 5
RATE_LIMIT_WINDOW_SECONDS = 60
TALLAS = {"XS", "S", "M", "L", "XL", "XXL"}

_orders = []
_orders_lock = Lock()
_request_times = {}
_rate_limit_lock = Lock()


@app.after_request
def identify_service_instance(response):
    response.headers["X-Service-Instance"] = SERVICE_INSTANCE_ID
    return response


def error(detail, status):
    return jsonify({"detail": detail}), status


def _is_positive_number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return isfinite(value) and value > 0
    except OverflowError:
        return False


def _validate_order(payload):
    if not isinstance(payload, dict):
        return "El cuerpo debe ser un objeto JSON"

    required = ("equipo", "talla", "presupuesto", "ingresos_mensuales", "plazos")
    missing = [field for field in required if field not in payload]
    if missing:
        return "Faltan campos: " + ", ".join(missing)
    if not isinstance(payload["equipo"], str) or not payload["equipo"].strip():
        return "El equipo debe ser un texto no vacío"
    if not isinstance(payload["talla"], str) or payload["talla"] not in TALLAS:
        return "La talla no es válida"
    if "temporada" in payload and (
        not isinstance(payload["temporada"], str)
        or not re.fullmatch(r"\d{4}/\d{2}", payload["temporada"])
    ):
        return "La temporada debe tener formato AAAA/AA, por ejemplo 2025/26"
    if not _is_positive_number(payload["presupuesto"]):
        return "El presupuesto debe ser un número mayor que 0"
    if not _is_positive_number(payload["ingresos_mensuales"]):
        return "Los ingresos_mensuales deben ser un número mayor que 0"
    if (
        not isinstance(payload["plazos"], int)
        or isinstance(payload["plazos"], bool)
        or not 1 <= payload["plazos"] <= 24
    ):
        return "Los plazos deben ser un entero entre 1 y 24"
    return None


def _limit_exceeded(api_key):
    now = monotonic()
    with _rate_limit_lock:
        timestamps = _request_times.setdefault(api_key, deque())
        while timestamps and now - timestamps[0] >= RATE_LIMIT_WINDOW_SECONDS:
            timestamps.popleft()
        if len(timestamps) >= MAX_REQUESTS_PER_MINUTE:
            return True, max(1, int(RATE_LIMIT_WINDOW_SECONDS - (now - timestamps[0])))
        timestamps.append(now)
        return False, None


@app.before_request
def protect_orders():
    if request.endpoint not in {"list_orders", "create_order"}:
        return None

    configured_key = app.config.get("API_KEY")
    supplied_key = request.headers.get("X-API-Key", "")
    if (
        not isinstance(configured_key, str)
        or not configured_key
        or not supplied_key.isascii()
        or not hmac.compare_digest(supplied_key, configured_key)
    ):
        return error("API key no válida o ausente", 401)

    exceeded, retry_after = _limit_exceeded(supplied_key)
    if exceeded:
        response, status = error("Límite de 5 peticiones por minuto superado", 429)
        response.headers["Retry-After"] = str(retry_after)
        return response, status
    return None


@app.errorhandler(404)
def not_found(_):
    return error("Recurso no encontrado", 404)


@app.errorhandler(405)
def method_not_allowed(_):
    return error("Método no permitido", 405)


def _detail_from(response, fallback):
    try:
        body = response.json()
    except ValueError:
        return fallback
    if isinstance(body, dict) and isinstance(body.get("detail"), str):
        return body["detail"]
    return fallback


def _service_error(response, service_name):
    if response.status_code in (400, 422):
        return error(_detail_from(response, "Solicitud no válida"), 400)
    if response.status_code == 404:
        return error(_detail_from(response, "Recurso no encontrado"), 404)
    if response.status_code == 409:
        return error(_detail_from(response, "Conflicto al procesar el pedido"), 409)
    if response.status_code >= 500:
        detail = _detail_from(response, f"El servicio de {service_name} no responde")
        return error(detail, 503)
    return error(f"Respuesta no válida del servicio de {service_name}", 503)


@app.get("/pedidos")
def list_orders():
    with _orders_lock:
        return jsonify(list(_orders))


@app.post("/pedidos")
def create_order():
    payload = request.get_json(silent=True)
    validation_error = _validate_order(payload)
    if validation_error:
        return error(validation_error, 400)

    team = payload["equipo"].strip()
    recommendation_request = {
        "equipo": team,
        "talla": payload["talla"],
        "presupuesto": payload["presupuesto"],
    }
    if "temporada" in payload:
        recommendation_request["temporada"] = payload["temporada"]
    try:
        recommendation_response = requests.post(
            f"{DECISION_URL}/recomendar",
            json=recommendation_request,
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        return error("El servicio de Decisión no responde", 503)

    if recommendation_response.status_code != 200:
        return _service_error(recommendation_response, "Decisión")
    try:
        recommendation_body = recommendation_response.json()
    except ValueError:
        return error("Respuesta no válida del servicio de Decisión", 503)
    if (
        not isinstance(recommendation_body, dict)
        or not isinstance(recommendation_body.get("recomendaciones"), list)
    ):
        return error("Respuesta no válida del servicio de Decisión", 503)

    recommendations = recommendation_body["recomendaciones"]
    if not recommendations:
        detail = recommendation_body.get("motivo")
        return error(
            detail if isinstance(detail, str) and detail else "No hay equipaciones disponibles",
            409,
        )

    equipment = recommendations[0]
    if not isinstance(equipment, dict) or not _is_positive_number(equipment.get("precio")):
        return error("Respuesta no válida del servicio de Decisión", 503)
    if not isinstance(equipment.get("id"), int) or isinstance(equipment.get("id"), bool):
        return error("Respuesta no válida del servicio de Decisión", 503)

    try:
        financing_response = requests.post(
            f"{DECISION_URL}/financiacion",
            json={
                "importe": equipment["precio"],
                "ingresos_mensuales": payload["ingresos_mensuales"],
                "plazos": payload["plazos"],
            },
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        return error("El servicio de Decisión no responde", 503)

    if financing_response.status_code != 200:
        return _service_error(financing_response, "Decisión")
    try:
        financing = financing_response.json()
    except ValueError:
        return error("Respuesta no válida del servicio de Decisión", 503)
    if not isinstance(financing, dict) or not isinstance(financing.get("aprobada"), bool):
        return error("Respuesta no válida del servicio de Decisión", 503)
    if not financing["aprobada"]:
        reason = financing.get("motivo")
        return error(
            reason if isinstance(reason, str) and reason else "La financiación no ha sido aprobada",
            400,
        )

    try:
        stock_response = requests.patch(
            f"{DATA_URL}/equipaciones/{equipment['id']}/stock",
            json={"delta": -1},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        return error("El servicio de Datos no responde", 503)

    if stock_response.status_code != 200:
        return _service_error(stock_response, "Datos")
    try:
        updated_equipment = stock_response.json()
    except ValueError:
        return error("Respuesta no válida del servicio de Datos", 503)
    if not isinstance(updated_equipment, dict):
        return error("Respuesta no válida del servicio de Datos", 503)

    order = {
        "equipacion": updated_equipment,
        "financiacion": financing,
        "ingresos_mensuales": payload["ingresos_mensuales"],
        "plazos": payload["plazos"],
    }
    with _orders_lock:
        order["id"] = len(_orders) + 1
        _orders.append(order)
    return jsonify(order), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
