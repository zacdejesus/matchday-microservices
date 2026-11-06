# Matchday · tienda de equipaciones con tres servicios REST

Proyecto del Equipo 4 (Programación de IA, FP Mercedarias): una tienda de equipaciones de fútbol hecha con **tres servicios REST** (Django, FastAPI y Flask) que se hablan por HTTP.

```
usuario --> PUERTA (:8000) --> DECISIÓN (:8002) --> DATOS (:8001)
               |                                        ^
               +----------------------------------------+
```

| Servicio | Quién | Framework | Puerto | Carpeta |
|---|---|---|---|---|
| 🗄 Datos | Antonio | Django | 8001 | `datos/` |
| 🧠 Decisión | Alejandro | FastAPI | 8002 | `decision/` |
| 🚪 Puerta | Evaristo | Flask | 8000 | `puerta/` |

**Entrega: hasta el 5 de noviembre.**

---

## 👋 Antonio y Evaristo: qué hay que hacer

### Paso 1 · Revisar el contrato (lo primero, antes de programar)

El borrador está en [`docs/contrato.md`](docs/contrato.md). Sin contrato no se programa: si un nombre de campo cambia después, los servicios dejan de entenderse.

- Leed vuestra sección y corregid lo que no os encaje (rutas, campos, códigos).
- Al final del contrato hay una lista **"Pendiente de decidir en equipo"**: hay que cerrarla entre los tres.
- **Frameworks:** Antonio usa Django, Evaristo usa Flask y Alejandro usa FastAPI. Así cumplimos el punto 1 del enunciado: los tres tienen que aparecer una vez en el equipo.

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
- `POST /pedidos` recibe `{equipo, talla, presupuesto, ingresos_mensuales, plazos}`. Pide recomendación y financiación a Decisión; si se aprueba, descuenta una unidad en Datos y guarda el pedido en memoria.
- Si no hay recomendaciones disponibles, responde **409**. Si la financiación no se aprueba, responde **400** con el motivo.
- El límite de 5 peticiones por minuto se comparte entre `GET` y `POST` para cada clave. `GET /pedidos` también puede responder **429** si se alcanza el límite.
- Si Datos informa de que no encuentra la equipación, Puerta devuelve **404**.
- Para ejecutar y probar Puerta, consulta [puerta/README.md](puerta/README.md).
- Las pruebas unitarias se ejecutan desde `puerta/` con `python -m unittest -v test_app.py`.
- El script de 10 peticiones para comprobar el límite está en [puerta/prueba_limite/](puerta/prueba_limite/); sus instrucciones están en [puerta/prueba_limite/README.md](puerta/prueba_limite/README.md).
- `test_integracion.py` (CU1–CU5) se prepara entre todos; Puerta lidera la comprobación del flujo completo.
- ⭐ Reto: un script que haga 10 peticiones seguidas y demuestre el límite (como *middleware* o dependencia).

## 🧠 Alejandro · Decisión (puerto 8002)

| Método | Ruta | Qué hace | Códigos |
|---|---|---|---|
| POST | `/recomendar` | Recibe `{equipo, presupuesto, talla, temporada?}`, consulta Datos y devuelve las 3 mejores | 200 · 422 · 503 |
| POST | `/financiacion` | Recibe `{importe, ingresos_mensuales, plazos}` y devuelve `{aprobada, cuota_mensual, motivo}` + reto: `interes_aplicado`, `total_a_pagar`, `explicacion` | 200 · 422 |
| GET | `/salud` | Comprueba que el servicio está vivo | 200 |

---

## ▶️ Cómo arrancar los tres servicios

Una terminal por servicio:

```bash
# Decisión (FastAPI) – documentación interactiva en http://localhost:8002/docs
cd decision
pip install -r requirements.txt
uvicorn main:app --port 8002 --reload
```
```bash
# Datos (Django), puerto 8001; en otra terminal, desde la raíz del repositorio
cd datos
pip install -r requirements.txt
python manage.py runserver 8001
```

```bash
# Puerta (Flask), puerto 8000; en otra terminal, desde la raíz del repositorio
cd puerta
pip install -r requirements.txt
API_KEY="una-clave-local" python app.py
```

En las peticiones a Puerta, envía `X-API-Key: una-clave-local` (o la misma
clave que hayas configurado en la variable `API_KEY`).

```bash
# Extra: tienda y panel de pruebas, puerto 8080; desde la raíz del repositorio
python front/servidor.py
# Tienda: http://localhost:8080 · Panel de pruebas: http://localhost:8080/panel
```

**En varios ordenadores:** cada servicio lee la dirección de los demás de variables
de entorno (`DATA_URL`, `DECISION_URL`, `PUERTA_URL`). Los pasos (IP, firewall,
`0.0.0.0`) están en [`hoja de ruta/despliegue-en-varios-ordenadores.md`](hoja%20de%20ruta/despliegue-en-varios-ordenadores.md).

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
matchday-microservices/
├── datos/
├── decision/
├── puerta/
├── front/            (extra: tienda y panel de pruebas)
├── docs/contrato.md
├── tests_integracion/
│   ├── test_integracion.py
│   ├── requirements.txt
│   └── README.md
└── README.md
```


## Alejandro · Decisión: framework y uso de IA

Se eligió **FastAPI** porque Decisión recibe datos que hay que validar con reglas
concretas (importe mayor que 0, plazos entre 1 y 24, talla de una lista) y FastAPI
lo hace de forma declarativa con modelos de pydantic: si algo no cumple, responde
422 sin escribir validaciones a mano. Además genera la documentación interactiva
en `/docs`, que sirvió para probar el servicio, y trabaja con tipos, algo familiar
viniendo de Swift.

Se usó IA (Claude Code) para generar el código de las rutas `/financiacion` y
`/recomendar` a partir del contrato: el cálculo de la cuota con el interés por
tramos, la explicación en lenguaje natural, la llamada a Datos con `requests` y
`timeout`, y el filtrado y ordenación de las recomendaciones. También se le pidió
un front extra (tienda y panel de pruebas) para ver qué servicio falla y con qué
código, y tambien se hizo uso de la IA para debuggear porque no se podia llegar los otros ordenadores
teniendo que hacer comandos en el terminal.


Lo que se revisó y cambió: se comprobó cada respuesta contra el contrato (el ejemplo
de 179,90 € en 6 plazos da 30,88 € de cuota y 185,30 € de total), cada tramo de
interés, los datos no válidos (422) y Datos apagado (503). Evaristo añadió después
el filtro opcional por `temporada` en `/recomendar`, que se revisó y probó. Con
los tres servicios en marcha pasan `test_integracion.py` y `puerta/test_app.py`.
