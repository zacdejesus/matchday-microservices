from django.shortcuts import render

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Aquí guardamos los datos "en memoria" (una lista)
EQUIPACIONES = [
    {"id": 1, "equipo": "Betis", "temporada": "2025/26", "talla": "M", "precio": 89.99, "stock": 10},
    {"id": 2, "equipo": "Sevilla", "temporada": "2025/26", "talla": "L", "precio": 84.99, "stock": 5},
    {"id": 3, "equipo": "Real Madrid", "temporada": "2025/26", "talla": "S", "precio": 99.99, "stock": 8},
]


@csrf_exempt
def lista_equipaciones(request):
    if request.method == "GET":
        equipo = request.GET.get("equipo")
        resultado = EQUIPACIONES

        if equipo:
            resultado = [e for e in EQUIPACIONES if e["equipo"].lower() == equipo.lower()]

        return JsonResponse(resultado, safe=False)

    if request.method == "POST":
        # 1. Leer el JSON que envían
        try:
            datos = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "JSON no válido"}, status=400)

        # 2. Comprobar que no falte ningún campo
        campos = ["equipo", "temporada", "talla", "precio", "stock"]
        faltan = [c for c in campos if c not in datos]
        if faltan:
            return JsonResponse({"error": "Faltan campos", "campos": faltan}, status=400)

        # 3. Comprobar que precio y stock sean números correctos
        if not isinstance(datos["precio"], (int, float)) or datos["precio"] <= 0:
            return JsonResponse({"error": "El precio debe ser un número mayor que 0"}, status=400)
        if not isinstance(datos["stock"], int) or datos["stock"] < 0:
            return JsonResponse({"error": "El stock debe ser un número entero, 0 o más"}, status=400)

        # 4. Crear la camiseta con un id nuevo
        nuevo_id = max([e["id"] for e in EQUIPACIONES], default=0) + 1
        nueva = {"id": nuevo_id, **{c: datos[c] for c in campos}}
        EQUIPACIONES.append(nueva)

        return JsonResponse(nueva, status=201)

    return JsonResponse({"error": "Método no permitido"}, status=405)