# Matchday · tienda de equipaciones con tres servicios REST

Proyecto del Equipo 4 (Programación de IA, FP Mercedarias): una tienda de equipaciones de fútbol hecha con **tres servicios REST** (Flask, FastAPI y Django) que se hablan por HTTP.

```
usuario --> PUERTA (:8000) --> DECISIÓN (:8002) --> DATOS (:8001)
               |                                        ^
               +----------------------------------------+
```

| Servicio | Quién | Framework | Puerto | Carpeta |
|---|---|---|---|---|
| 🗄 Datos | Antonio | Flask o Django (a decidir) | 8001 | `datos/` |
| 🧠 Decisión | Alejandro | FastAPI | 8002 | `decision/` |
| 🚪 Puerta | Evaristo | Flask o Django (a decidir) | 8000 | `puerta/` |

**Entrega: hasta el 5 de noviembre.**

---

## 👋 Antonio y Evaristo: qué hay que hacer

### Paso 1 · Revisar el contrato (lo primero, antes de programar)

El borrador está en [`docs/contrato.md`](docs/contrato.md). Sin contrato no se programa: si un nombre de campo cambia después, los servicios dejan de entenderse.

- Leed vuestra sección y corregid lo que no os encaje (rutas, campos, códigos).
- Al final del contrato hay una lista **"Pendiente de decidir en equipo"**: hay que cerrarla entre los tres.
- **Elegid framework:** Decisión ya usa FastAPI, así que entre vosotros dos tiene que haber un Flask y un Django.

### Paso 2 · Clonar el repo

```bash
git clone https://github.com/zacdejesus/matchday-microservices.git
cd matchday-microservices
```

### Paso 3 · Programar vuestro servicio, cada uno en su carpeta

- **Cada uno toca solo su carpeta.** Así casi no hay conflictos de Git.
- **Nunca se importa el código de otro servicio.** Para pedir algo a un compañero, se llama por HTTP con `requests`.
- Siempre con `timeout=3` y capturando `requests.RequestException`. Si el otro servicio no responde, se devuelve **503**.
- Cada servicio guarda sus datos **en memoria o en su propio JSON** dentro de su carpeta.
- Añadid un `requirements.txt` en vuestra carpeta con lo que haga falta.
- Los errores van siempre con el mismo formato: `{ "detail": "mensaje" }`.

### Paso 4 · Subir los cambios

```bash
git pull                 # traer lo de los demás antes de empezar
git add datos/           # o puerta/
git commit -m "Add GET /equipaciones"
git push
```

---

## 🗄 Antonio · Datos (puerto 8001)

El catálogo: es el **único** servicio que guarda las equipaciones.

| Método | Ruta | Qué hace | Códigos |
|---|---|---|---|
| GET | `/equipaciones?equipo=Betis` | Lista y filtra | 200 |
| POST | `/equipaciones` | Crea (`equipo`, `temporada`, `talla`, `precio`, `stock`) | 201 · 400 |
| GET | `/equipaciones/{id}` | Una equipación | 200 · 404 |
| PUT | `/equipaciones/{id}` | La modifica | 200 · 400 · 404 |
| DELETE | `/equipaciones/{id}` | La elimina | 204 · 404 |
| PATCH | `/equipaciones/{id}/stock` | Suma o resta unidades (`{delta}`) | 200 · 404 · 409 |

- ⚠️ **Importante para Decisión:** `GET /equipaciones` debe devolver exactamente los campos `id, equipo, temporada, talla, precio, stock` (ver el contrato).
- 409 si el stock quedaría por debajo de 0.
- ⭐ Reto: 10 equipaciones de equipos reales y el filtro `?max_precio=60`.

## 🚪 Evaristo · Puerta (puerto 8000)

Lo que ve el usuario: orquesta el flujo y protege la API.

| Método | Ruta | Qué hace | Códigos |
|---|---|---|---|
| POST | `/pedidos` | Requiere la cabecera `X-API-Key`. Pide recomendación y financiación a Decisión, descuenta el stock en Datos y crea el pedido | 201 · 400 · 401 · 409 · 429 · 503 |
| GET | `/pedidos` | Lista los pedidos | 200 · 401 |

- Sin clave o con clave incorrecta: **401**. Más de 5 peticiones por minuto con la misma clave: **429**.
- Si Decisión o Datos no responden: **503** con un mensaje que diga cuál.
- El flujo de `POST /pedidos` está propuesto en el contrato: confírmalo.
- `test_integracion.py` (CU1–CU5) lo hacemos entre todos, pero lo lógico es que lo lidere Puerta.
- ⭐ Reto: un script que haga 10 peticiones seguidas y demuestre el límite (como *middleware* o dependencia).

## 🧠 Alejandro · Decisión (puerto 8002)

| Método | Ruta | Qué hace | Códigos |
|---|---|---|---|
| POST | `/recomendar` | Recibe `{equipo, presupuesto, talla}`, consulta Datos y devuelve las 3 mejores | 200 · 422 · 503 |
| POST | `/financiacion` | Recibe `{importe, ingresos_mensuales, plazos}` y devuelve `{aprobada, cuota_mensual, motivo}` | 200 · 422 |
| GET | `/salud` | Comprueba que el servicio está vivo | 200 |

---

## ▶️ Cómo arrancar los tres servicios

Una terminal por servicio:

```bash
# Decisión (FastAPI) – documentación interactiva en http://localhost:8002/docs
cd decision
pip install -r requirements.txt
uvicorn main:app --port 8002 --reload

# Datos – (Antonio: completar)

# Puerta – (Evaristo: completar)
```

## ✅ Casos de uso que tiene que cumplir el equipo

| Caso | Qué se comprueba |
|---|---|
| CU1 | Consultar datos a través de la Puerta (`GET`) |
| CU2 | Crear un recurso con validación: si faltan campos, 400/422 |
| CU3 | Flujo completo Puerta → Decisión → Datos con respuesta 201 |
| CU4 | Recurso inexistente: el 404 llega bien hasta el usuario |
| CU5 | Se apaga un servicio: la Puerta responde 503 con un mensaje claro |
| CU6 | `test_integracion.py` con `requests` que comprueba CU1–CU5 |

## 📦 Entrega

Un `.zip` con esta estructura, que sube cada integrante a Teams:

```
equipo_4/
├── datos/
├── decision/
├── puerta/
├── docs/contrato.md
├── test_integracion.py
└── README.md
```

## Pendiente para el README final

- [ ] Por qué cada uno eligió su framework.
- [ ] Cómo arrancar Datos y Puerta.
- [ ] **Uso de IA:** qué le preguntamos y qué cambiamos de lo que nos respondió (cada uno su parte).
