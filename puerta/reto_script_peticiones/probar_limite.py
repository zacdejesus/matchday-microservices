"""Send 10 consecutive requests and verify Puerta's rate limit."""

import os
import sys

import requests

URL = os.environ.get("PUERTA_URL", "http://localhost:8000/pedidos")
API_KEY = os.environ.get("API_KEY")
REQUEST_COUNT = 10
ALLOWED_REQUESTS = 5


def main():
    if not API_KEY:
        print("Error: configura API_KEY con la misma clave que usa Puerta.")
        return 1

    statuses = []
    for number in range(1, REQUEST_COUNT + 1):
        try:
            response = requests.get(
                URL,
                headers={"X-API-Key": API_KEY},
                timeout=3,
            )
        except requests.RequestException as exc:
            print(f"Error en la petición {number}: {exc}")
            return 1

        statuses.append(response.status_code)
        line = f"Petición {number}: HTTP {response.status_code}"
        if response.status_code == 429 and response.headers.get("Retry-After"):
            line += f" (Retry-After: {response.headers['Retry-After']} s)"
        print(line)

    expected = [200] * ALLOWED_REQUESTS + [429] * (REQUEST_COUNT - ALLOWED_REQUESTS)
    if statuses == expected:
        print("\nCorrecto: las primeras 5 peticiones pasan y las siguientes 5 reciben 429.")
        return 0

    print("\nNo se obtuvo el patrón esperado de 5 respuestas 200 y 5 respuestas 429.")
    if all(status == 429 for status in statuses[: REQUEST_COUNT - ALLOWED_REQUESTS]):
        print(
            "La clave probablemente ya tenía peticiones recientes. "
            "Reinicia Puerta o espera 60 segundos sin usarla y repite la prueba."
        )
    elif any(status == 401 for status in statuses):
        print("Comprueba que API_KEY coincide con la variable configurada en Puerta.")
    else:
        print(f"Códigos recibidos: {statuses}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
