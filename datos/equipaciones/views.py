import json
import re
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

EQUIPACIONES = [
    {"id": 1, "equipo": "Betis", "temporada": "2025/26", "talla": "M", "precio": 89.99, "stock": 10},
    {"id": 2, "equipo": "Sevilla", "temporada": "2025/26", "talla": "L", "precio": 84.99, "stock": 5},
    {"id": 3, "equipo": "Real Madrid", "temporada": "2025/26", "talla": "S", "precio": 99.99, "stock": 8},
]

CAMPOS = ["equipo", "temporada", "talla", "precio", "stock"]
TALLAS = ["XS", "S", "M", "L", "XL", "XXL"]


def error(mensaje, codigo):
    """Todos los errores tienen el mismo formato: {"detail": "..."}"""
    return JsonResponse({"detail": mensaje}, status=codigo)


def es_numero(valor):
    # En Python, True y False cuentan como números, así que los descartamos
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def es_entero(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


def leer_y_validar(request):
    """Devuelve (datos, None) si todo va bien, o (None, respuesta_de_error) si algo falla."""
    try:
        datos = json.loads(request.body)
    except json.JSONDecodeError:
        return None, error("JSON no válido", 400)

    if not isinstance(datos, dict):
        return None, error("Se esperaba un objeto JSON", 400)

    faltan = [c for c in CAMPOS if c not in datos]
    if faltan:
        return None, error("Faltan campos: " + ", ".join(faltan), 400)

    if not isinstance(datos["equipo"], str) or not datos["equipo"].strip():
        return None, error("El equipo debe ser un texto no vacío", 400)

    if not isinstance(datos["temporada"], str) or not re.fullmatch(r"\d{4}/\d{2}", datos["temporada"]):
        return None, error("La temporada debe tener formato AAAA/AA, por ejemplo 2025/26", 400)

    if datos["talla"] not in TALLAS:
        return None, error("La talla debe ser una de: " + ", ".join(TALLAS), 400)

    if not es_numero(datos["precio"]) or datos["precio"] <= 0:
        return None, error("El precio debe ser un número mayor que 0", 400)

    if not es_entero(datos["stock"]) or datos["stock"] < 0:
        return None, error("El stock debe ser un número entero, 0 o más", 400)

    return datos, None


@csrf_exempt
def lista_equipaciones(request):
    if request.method == "GET":
        equipo = request.GET.get("equipo")
        resultado = EQUIPACIONES
        if equipo:
            resultado = [e for e in EQUIPACIONES if e["equipo"].lower() == equipo.lower()]
        return JsonResponse(resultado, safe=False)

    if request.method == "POST":
        datos, fallo = leer_y_validar(request)
        if fallo:
            return fallo

        nuevo_id = max([e["id"] for e in EQUIPACIONES], default=0) + 1
        nueva = {"id": nuevo_id, **{c: datos[c] for c in CAMPOS}}
        EQUIPACIONES.append(nueva)
        return JsonResponse(nueva, status=201)

    return error("Método no permitido", 405)


@csrf_exempt
def detalle_equipacion(request, id):
    equipacion = next((e for e in EQUIPACIONES if e["id"] == id), None)
    if equipacion is None:
        return error("Equipación no encontrada", 404)

    if request.method == "GET":
        return JsonResponse(equipacion)

    if request.method == "PUT":
        datos, fallo = leer_y_validar(request)
        if fallo:
            return fallo
        for c in CAMPOS:
            equipacion[c] = datos[c]
        return JsonResponse(equipacion)

    if request.method == "DELETE":
        EQUIPACIONES.remove(equipacion)
        return HttpResponse(status=204)

    return error("Método no permitido", 405)


@csrf_exempt
def cambiar_stock(request, id):
    if request.method != "PATCH":
        return error("Método no permitido", 405)

    equipacion = next((e for e in EQUIPACIONES if e["id"] == id), None)
    if equipacion is None:
        return error("Equipación no encontrada", 404)

    try:
        datos = json.loads(request.body)
    except json.JSONDecodeError:
        return error("JSON no válido", 400)

    if not isinstance(datos, dict) or "delta" not in datos:
        return error("Falta el campo delta", 400)

    if not es_entero(datos["delta"]):
        return error("delta debe ser un número entero", 400)

    nuevo_stock = equipacion["stock"] + datos["delta"]
    if nuevo_stock < 0:
        return error("Stock insuficiente: quedan " + str(equipacion["stock"]) + " unidades", 409)

    equipacion["stock"] = nuevo_stock
    return JsonResponse(equipacion)