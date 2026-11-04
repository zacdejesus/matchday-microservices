import unittest
from unittest.mock import Mock, patch

import app as puerta


def http_response(status_code, body):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = body
    return response


class PuertaTests(unittest.TestCase):
    def setUp(self):
        puerta.app.config.update(TESTING=True, API_KEY="clave-de-prueba")
        puerta._orders.clear()
        puerta._request_times.clear()
        self.client = puerta.app.test_client()
        self.headers = {"X-API-Key": "clave-de-prueba"}

    def test_orders_require_api_key(self):
        response = self.client.get("/pedidos")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json, {"detail": "API key no válida o ausente"})

    def test_wrong_api_key_is_rejected(self):
        response = self.client.get("/pedidos", headers={"X-API-Key": "incorrecta"})
        self.assertEqual(response.status_code, 401)

    def test_non_ascii_api_key_is_rejected(self):
        response = self.client.get("/pedidos", headers={"X-API-Key": "clávé"})
        self.assertEqual(response.status_code, 401)

    def test_rate_limit_is_shared_by_order_routes(self):
        for _ in range(5):
            self.assertEqual(self.client.get("/pedidos", headers=self.headers).status_code, 200)

        for _ in range(5):
            response = self.client.post("/pedidos", headers=self.headers, json={})
            self.assertEqual(response.status_code, 429)
            self.assertIn("Retry-After", response.headers)

    def test_missing_fields_return_400(self):
        response = self.client.post(
            "/pedidos",
            headers=self.headers,
            json={"equipo": "Betis", "presupuesto": 100},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["detail"], "Faltan campos: talla, ingresos_mensuales, plazos")

    def test_invalid_talla_type_returns_400(self):
        response = self.client.post(
            "/pedidos",
            headers=self.headers,
            json={
                "equipo": "Betis",
                "talla": [],
                "presupuesto": 100,
                "ingresos_mensuales": 1200,
                "plazos": 6,
            },
        )
        self.assertEqual(response.status_code, 400)

    @patch.object(puerta.requests, "patch")
    @patch.object(puerta.requests, "post")
    def test_valid_order_calls_services_and_is_listed(self, post, patch_stock):
        post.side_effect = [
            http_response(
                200,
                {
                    "recomendaciones": [
                        {
                            "id": 2,
                            "equipo": "Betis",
                            "temporada": "2024/25",
                            "talla": "M",
                            "precio": 59.95,
                            "stock": 4,
                        }
                    ],
                    "motivo": "Una equipación disponible",
                },
            ),
            http_response(200, {"aprobada": True, "cuota_mensual": 9.99, "motivo": "Aprobada"}),
        ]
        patch_stock.return_value = http_response(
            200,
            {
                "id": 2,
                "equipo": "Betis",
                "temporada": "2024/25",
                "talla": "M",
                "precio": 59.95,
                "stock": 3,
            },
        )

        response = self.client.post(
            "/pedidos",
            headers=self.headers,
            json={
                "equipo": " Betis ",
                "talla": "M",
                "presupuesto": 100,
                "ingresos_mensuales": 1200,
                "plazos": 6,
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["id"], 1)
        self.assertEqual(response.json["equipacion"]["stock"], 3)
        self.assertEqual(post.call_count, 2)
        self.assertEqual(post.call_args_list[0].kwargs["timeout"], 3)
        self.assertEqual(post.call_args_list[1].kwargs["timeout"], 3)
        patch_stock.assert_called_once_with(
            "http://localhost:8001/equipaciones/2/stock",
            json={"delta": -1},
            timeout=3,
        )
        listed = self.client.get("/pedidos", headers=self.headers)
        self.assertEqual(listed.json, [response.json])

    @patch.object(puerta.requests, "post")
    def test_no_recommendation_returns_409(self, post):
        post.return_value = http_response(
            200, {"recomendaciones": [], "motivo": "No hay equipaciones del Betis"}
        )
        response = self.client.post(
            "/pedidos",
            headers=self.headers,
            json={
                "equipo": "Betis",
                "talla": "M",
                "presupuesto": 100,
                "ingresos_mensuales": 1200,
                "plazos": 6,
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["detail"], "No hay equipaciones del Betis")
        self.assertEqual(post.call_count, 1)

    @patch.object(puerta.requests, "patch")
    @patch.object(puerta.requests, "post")
    def test_rejected_financing_returns_400_without_changing_stock(self, post, patch_stock):
        post.side_effect = [
            http_response(200, {"recomendaciones": [{"id": 2, "precio": 59.95}]}),
            http_response(200, {"aprobada": False, "motivo": "Ingresos insuficientes"}),
        ]
        response = self.client.post(
            "/pedidos",
            headers=self.headers,
            json={
                "equipo": "Betis",
                "talla": "M",
                "presupuesto": 100,
                "ingresos_mensuales": 100,
                "plazos": 1,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["detail"], "Ingresos insuficientes")
        patch_stock.assert_not_called()

    @patch.object(puerta.requests, "post", side_effect=puerta.requests.Timeout)
    def test_decision_timeout_returns_503(self, post):
        response = self.client.post(
            "/pedidos",
            headers=self.headers,
            json={
                "equipo": "Betis",
                "talla": "M",
                "presupuesto": 100,
                "ingresos_mensuales": 1200,
                "plazos": 6,
            },
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["detail"], "El servicio de Decisión no responde")
        post.assert_called_once()

    @patch.object(puerta.requests, "post")
    def test_data_failure_reported_by_decision_keeps_data_service_name(self, post):
        post.return_value = http_response(
            503, {"detail": "El servicio de Datos no responde"}
        )
        response = self.client.post(
            "/pedidos",
            headers=self.headers,
            json={
                "equipo": "Betis",
                "talla": "M",
                "presupuesto": 100,
                "ingresos_mensuales": 1200,
                "plazos": 6,
            },
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["detail"], "El servicio de Datos no responde")

    def test_unknown_route_returns_json_error(self):
        response = self.client.get("/no-existe")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json, {"detail": "Recurso no encontrado"})

    @patch.object(puerta.requests, "patch")
    @patch.object(puerta.requests, "post")
    def test_stock_conflict_is_returned_without_creating_order(self, post, patch_stock):
        post.side_effect = [
            http_response(200, {"recomendaciones": [{"id": 2, "precio": 59.95}]}),
            http_response(200, {"aprobada": True}),
        ]
        patch_stock.return_value = http_response(409, {"detail": "Stock insuficiente"})

        response = self.client.post(
            "/pedidos",
            headers=self.headers,
            json={
                "equipo": "Betis",
                "talla": "M",
                "presupuesto": 100,
                "ingresos_mensuales": 1200,
                "plazos": 6,
            },
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["detail"], "Stock insuficiente")
        self.assertEqual(puerta._orders, [])

    @patch.object(puerta.requests, "patch")
    @patch.object(puerta.requests, "post")
    def test_missing_equipment_is_returned_as_404(self, post, patch_stock):
        post.side_effect = [
            http_response(200, {"recomendaciones": [{"id": 999, "precio": 59.95}]}),
            http_response(200, {"aprobada": True}),
        ]
        patch_stock.return_value = http_response(404, {"detail": "Equipación no encontrada"})

        response = self.client.post(
            "/pedidos",
            headers=self.headers,
            json={
                "equipo": "Betis",
                "talla": "M",
                "presupuesto": 100,
                "ingresos_mensuales": 1200,
                "plazos": 6,
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json["detail"], "Equipación no encontrada")
        self.assertEqual(puerta._orders, [])


if __name__ == "__main__":
    unittest.main()
