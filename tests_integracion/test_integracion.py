"""Black-box integration checks for Puerta against the running services."""

import os
import unittest

import requests

PUERTA_URL = os.environ.get("PUERTA_URL", "http://localhost:8000").rstrip("/")
DATA_URL = os.environ.get("DATA_URL", "http://localhost:8001").rstrip("/")
API_KEY = os.environ.get("API_KEY", "clave-local")
RUN_CU5 = os.environ.get("PROBAR_CU5") == "1"
TIMEOUT_SECONDS = 3

ORDER_BODY = {
    "equipo": "Betis",
    "talla": "M",
    "presupuesto": 100,
    "ingresos_mensuales": 1200,
    "plazos": 6,
}


class PuertaIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.headers = {"X-API-Key": API_KEY}

    def test_00_authentication_requires_a_valid_key(self):
        without_key = requests.get(
            f"{PUERTA_URL}/pedidos",
            timeout=TIMEOUT_SECONDS,
        )
        wrong_key = requests.get(
            f"{PUERTA_URL}/pedidos",
            headers={"X-API-Key": f"{API_KEY}-incorrecta"},
            timeout=TIMEOUT_SECONDS,
        )

        self.assertEqual(without_key.status_code, 401)
        self.assertEqual(wrong_key.status_code, 401)

    def test_cu1_list_orders_with_valid_key(self):
        response = requests.get(
            f"{PUERTA_URL}/pedidos",
            headers=self.headers,
            timeout=TIMEOUT_SECONDS,
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsInstance(response.json(), list)

    def test_cu2_missing_size_is_rejected(self):
        body = {
            "equipo": "Betis",
            "presupuesto": 100,
            "ingresos_mensuales": 1200,
            "plazos": 6,
        }
        response = requests.post(
            f"{PUERTA_URL}/pedidos",
            headers=self.headers,
            json=body,
            timeout=TIMEOUT_SECONDS,
        )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("detail", response.json())

    @unittest.skipIf(RUN_CU5, "CU3 necesita Datos activo; CU5 se ejecuta por separado.")
    def test_cu3_valid_order_traverses_decision_and_data(self):
        response = requests.post(
            f"{PUERTA_URL}/pedidos",
            headers=self.headers,
            json=ORDER_BODY,
            timeout=TIMEOUT_SECONDS,
        )

        self.assertEqual(response.status_code, 201, response.text)
        order = response.json()
        self.assertIn("id", order)
        self.assertIn("equipacion", order)
        self.assertEqual(order["equipacion"]["equipo"], ORDER_BODY["equipo"])

    @unittest.skipIf(RUN_CU5, "CU4 necesita Datos activo; CU5 se ejecuta por separado.")
    def test_cu4_no_matching_equipment_returns_409(self):
        body = {**ORDER_BODY, "equipo": "EquipoQueNoExiste"}
        response = requests.post(
            f"{PUERTA_URL}/pedidos",
            headers=self.headers,
            json=body,
            timeout=TIMEOUT_SECONDS,
        )

        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn("detail", response.json())

    @unittest.skipUnless(
        RUN_CU5,
        "Para CU5, apaga Datos y ejecuta con PROBAR_CU5=1.",
    )
    def test_cu5_data_unavailable_returns_503(self):
        try:
            data_response = requests.get(
                f"{DATA_URL}/equipaciones",
                timeout=TIMEOUT_SECONDS,
            )
        except requests.RequestException:
            pass
        else:
            self.fail(
                f"Datos sigue respondiendo (HTTP {data_response.status_code}) en "
                f"{DATA_URL}. Detén el servidor de Datos en su terminal y vuelve "
                "a ejecutar CU5; no se ha enviado ningún pedido."
            )

        response = requests.post(
            f"{PUERTA_URL}/pedidos",
            headers=self.headers,
            json=ORDER_BODY,
            timeout=TIMEOUT_SECONDS,
        )

        self.assertEqual(response.status_code, 503, response.text)
        self.assertIn("Datos", response.json().get("detail", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
