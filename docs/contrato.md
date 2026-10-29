# Contrato REST – Equipo 4 · Tienda de equipaciones

Antonio (Datos) · Alejandro de Jesús (Decisión) · Evaristo (Puerta)

> Borrador. Cada uno completa y revisa su sección; lo cerramos entre los tres antes de programar.

## Arquitectura

```
usuario --> PUERTA (:8000) --> DECISIÓN (:8002) --> DATOS (:8001)
               |                                        ^
               +----------------------------------------+
```

| Servicio | Responsable | Framework | Puerto |
|---|---|---|---|
| Datos | Antonio | Django | 8001 |
| Decisión | Alejandro | FastAPI | 8002 |
| Puerta | Evaristo | Flask | 8000 |

## Convenciones comunes

- Todo el cuerpo de las peticiones y respuestas va en JSON (`Content-Type: application/json`).
- Rutas en plural y en minúsculas.
- Importes en euros, como número (`59.95`), nunca como texto.
- **Formato de error**, igual en los tres servicios:

  ```json
  { "detail": "Mensaje claro para el usuario" }
  ```

  (Es el formato que FastAPI usa por defecto; en otros frameworks se devuelve igual a mano.)
- **Datos mal enviados:** 400, o 422 en FastAPI (validación automática de pydantic). Puerta trata 400 y 422 igual.
- Llamadas entre servicios: siempre con `requests`, `timeout=3` y captura de `requests.RequestException`. Si el otro servicio no responde → **503**.

---

## 🗄 Datos (Antonio, puerto 8001)

### Modelo de una equipación

```json
{
  "id": 1,
  "equipo": "Betis",
  "temporada": "2025/26",
  "talla": "M",
  "precio": 89.95,
  "stock": 12
}
```

- `talla`: una de `XS`, `S`, `M`, `L`, `XL`, `XXL`.
- `temporada`: texto con formato `AAAA/AA`.

| Método | Ruta | Entrada | Salida | Códigos |
|---|---|---|---|---|
| GET | `/equipaciones?equipo=Betis` | – | lista de equipaciones (filtro opcional) | 200 |
| POST | `/equipaciones` | `{equipo, temporada, talla, precio, stock}` | la equipación creada, con `id` | 201 · 400 |
| GET | `/equipaciones/{id}` | – | una equipación | 200 · 404 |
| PUT | `/equipaciones/{id}` | `{equipo, temporada, talla, precio, stock}` | la equipación modificada | 200 · 400 · 404 |
| DELETE | `/equipaciones/{id}` | – | sin cuerpo | 204 · 404 |
| PATCH | `/equipaciones/{id}/stock` | `{delta}` (ej. `-1`) | la equipación con el stock nuevo | 200 · 404 · 409 |

- 409 si el stock quedaría por debajo de 0.
- (Antonio: completa ejemplos y el reto `?max_precio=60`.)

---

## 🧠 Decisión (Alejandro, puerto 8002)

### POST `/recomendar`

Recibe lo que busca el cliente, pide a Datos las equipaciones de ese equipo y devuelve las 3 mejores.

**Entrada**

```json
{ "equipo": "Betis", "presupuesto": 100, "talla": "M" }
```

| Campo | Tipo | Regla |
|---|---|---|
| `equipo` | texto | obligatorio, no vacío |
| `presupuesto` | número | obligatorio, mayor que 0 |
| `talla` | texto | una de `XS`, `S`, `M`, `L`, `XL`, `XXL` |

**Qué hace**

1. Llama a Datos: `GET http://localhost:8001/equipaciones?equipo={equipo}`.
2. Se queda con las que tienen esa `talla`, `precio <= presupuesto` y `stock > 0`.
3. Ordena: primero la temporada más reciente; a igual temporada, la más barata.
4. Devuelve como máximo 3.

**Salida 200**

```json
{
  "recomendaciones": [
    { "id": 3, "equipo": "Betis", "temporada": "2025/26", "talla": "M", "precio": 89.95, "stock": 12 },
    { "id": 7, "equipo": "Betis", "temporada": "2024/25", "talla": "M", "precio": 59.95, "stock": 4 }
  ],
  "motivo": "2 equipaciones del Betis en talla M por 100 € o menos, de la más nueva a la más antigua"
}
```

Si ninguna cumple, también es 200, con `"recomendaciones": []` y un `motivo` que explica por qué.

**Códigos**

| Código | Cuándo |
|---|---|
| 200 | Todo bien (aunque la lista esté vacía) |
| 422 | Falta un campo o tiene un valor no válido |
| 503 | Datos no responde: `{ "detail": "El servicio de Datos no responde" }` |

### POST `/financiacion`

Decide si se puede pagar a plazos.

**Entrada**

```json
{ "importe": 179.90, "ingresos_mensuales": 1200, "plazos": 6 }
```

| Campo | Tipo | Regla |
|---|---|---|
| `importe` | número | mayor que 0 |
| `ingresos_mensuales` | número | mayor que 0 |
| `plazos` | entero | entre 1 y 24 |

**Regla:** se aprueba si `cuota_mensual <= 30 % de ingresos_mensuales`.

**Salida 200**

```json
{
  "aprobada": true,
  "cuota_mensual": 30.88,
  "motivo": "La cuota (30,88 €) es el 2,6 % de tus ingresos, por debajo del límite del 30 %"
}
```

**Códigos:** 200 · 422 (datos no válidos).

**Reto (+1):** interés según el plazo y explicación en lenguaje natural. La respuesta añade:

```json
{
  "interes_aplicado": 0.03,
  "total_a_pagar": 185.30,
  "explicacion": "Pagarías 6 cuotas de 30,88 €. Al ser más de 3 plazos se aplica un 3 % de interés..."
}
```

| Plazos | Interés sobre el importe |
|---|---|
| 1–3 | 0 % |
| 4–6 | 3 % |
| 7–12 | 6 % |
| 13–24 | 10 % |

`cuota_mensual = importe × (1 + interés) / plazos`, redondeada a 2 decimales.

### GET `/salud` (extra)

Devuelve `{ "estado": "ok" }`. Sirve para que Puerta compruebe si Decisión está viva.

---

## 🚪 Puerta (Evaristo, puerto 8000)

| Método | Ruta | Entrada | Salida | Códigos |
|---|---|---|---|---|
| POST | `/pedidos` | cabecera `X-API-Key` + `{equipo, talla, presupuesto, ingresos_mensuales, plazos}` (a confirmar) | el pedido creado | 201 · 400 · 401 · 409 · 429 · 503 |
| GET | `/pedidos` | cabecera `X-API-Key` | lista de pedidos | 200 · 401 |

- Sin clave o con clave incorrecta: 401. Más de 5 peticiones por minuto con la misma clave: 429.
- Flujo de `POST /pedidos` (Evaristo, confirma):
  1. `POST :8002/recomendar` → si la lista está vacía, 409 (no hay nada que vender).
  2. Elige la primera recomendación.
  3. `POST :8002/financiacion` con su `precio` → si `aprobada` es `false`, 400 (o el código que acordemos) con el `motivo`.
  4. `PATCH :8001/equipaciones/{id}/stock` con `{ "delta": -1 }` → si 409, sin stock.
  5. Guarda el pedido y responde 201.
- Si Decisión o Datos no responden: 503 con un mensaje que diga cuál.

---

## Casos de uso (CU1–CU6)

| Caso | Prueba concreta |
|---|---|
| CU1 | `GET :8000/pedidos` con clave válida → 200 |
| CU2 | `POST :8000/pedidos` sin `talla` → 400/422 |
| CU3 | `POST :8000/pedidos` válido → recorre Decisión y Datos → 201 |
| CU4 | Pedido de una equipación que no existe → 404 hasta el usuario |
| CU5 | Apagamos Datos → Puerta responde 503 con un mensaje claro |
| CU6 | `test_integracion.py` comprueba CU1–CU5 |

## Pendiente de decidir en equipo

- [x] Qué framework usa cada uno: Antonio Django, Evaristo Flask, Alejandro FastAPI.
- [ ] Código cuando la financiación no se aprueba en `POST /pedidos`.
- [ ] Campos exactos de entrada de `POST /pedidos`.
- [ ] Qué devuelve CU4 exactamente (¿qué recurso inexistente probamos?).
