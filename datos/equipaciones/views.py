import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

EQUIPACIONES = [
    {"id": 1, "equipo": "Betis", "temporada": "2025/26", "talla": "M", "precio": 89.99, "stock": 10},
    {"id": 2, "equipo": "Sevilla", "temporada": "2025/26", "talla": "L", "precio": 84.99, "stock": 5},
    {"id": 3, "equipo": "Real Madrid", "temporada": "2025/26", "talla": "S", "precio": 99.99, "stock": 8},
]

CAMPOS = ["equipo", "temporada", "talla", "precio", "stock"]


def leer_y_validar(request):
    """Devuelve (datos, None) si todo va bien, o (None, error) si hay algo mal."""
    try:
        datos = json.loads(request.body)
    except json.JSONDecodeError:
        return None, JsonResponse({"error": "JSON no válido"}, status=400)

    if not isinstance(datos, dict):
        return None, JsonResponse({"error": "Se esperaba un objeto JSON"}, status=400)

    faltan = [c for c in CAMPOS if c not in datos]
    if faltan:
        return None, JsonResponse({"error": "Faltan campos", "campos": faltan}, status=400)

    if not isinstance(datos["precio"], (int, float)) or datos["precio"] <= 0:
        return None, JsonResponse({"error": "El precio debe ser un número mayor que 0"}, status=400)

    if not isinstance(datos["stock"], int) or datos["stock"] < 0:
        return None, JsonResponse({"error": "El stock debe ser un número entero, 0 o más"}, status=400)

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
        datos, error = leer_y_validar(request)
        if error:
            return error

        nuevo_id = max([e["id"] for e in EQUIPACIONES], default=0) + 1
        nueva = {"id": nuevo_id, **{c: datos[c] for c in CAMPOS}}
        EQUIPACIONES.append(nueva)
        return JsonResponse(nueva, status=201)

    return JsonResponse({"error": "Método no permitido"}, status=405)


@csrf_exempt
def detalle_equipacion(request, id):
    # Buscamos la camiseta con ese id
    equipacion = next((e for e in EQUIPACIONES if e["id"] == id), None)
    if equipacion is None:
        return JsonResponse({"error": "Equipación no encontrada"}, status=404)

    if request.method == "GET":
        return JsonResponse(equipacion)

    if request.method == "PUT":
        datos, error = leer_y_validar(request)
        if error:
            return error
        for c in CAMPOS:
            equipacion[c] = datos[c]
        return JsonResponse(equipacion)

    if request.method == "DELETE":
        EQUIPACIONES.remove(equipacion)
        return HttpResponse(status=204)

    return JsonResponse({"error": "Método no permitido"}, status=405)

@csrf_exempt
def cambiar_stock(request, id):
    if request.method != "PATCH":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    equipacion = next((e for e in EQUIPACIONES if e["id"] == id), None)
    if equipacion is None:
        return JsonResponse({"error": "Equipación no encontrada"}, status=404)

    try:
        datos = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON no válido"}, status=400)

    if not isinstance(datos, dict) or "delta" not in datos:
        return JsonResponse({"error": "Falta el campo delta"}, status=400)

    delta = datos["delta"]
    if isinstance(delta, bool) or not isinstance(delta, int):
        return JsonResponse({"error": "delta debe ser un número entero"}, status=400)

    nuevo_stock = equipacion["stock"] + delta
    if nuevo_stock < 0:
        return JsonResponse(
            {"error": "Stock insuficiente", "stock_actual": equipacion["stock"]},
            status=409,
        )

    equipacion["stock"] = nuevo_stock
    return JsonResponse(equipacion)