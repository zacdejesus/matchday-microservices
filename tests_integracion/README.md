# Pruebas de integración de Puerta

Estas pruebas llaman a los servicios HTTP reales; no simulan Decisión ni Datos.
Arranca Datos, Decisión y Puerta antes de probar CU1–CU4. Desde la raíz del
repositorio, instala `requests` y ejecuta:

```bash
pip install -r tests_integracion/requirements.txt
API_KEY="una-clave-local" python -m unittest discover \
  -s tests_integracion -p "test_integracion.py" -v
```

`API_KEY` debe coincidir con la clave usada al iniciar Puerta. Si Puerta está
en otra dirección, puedes cambiarla con `PUERTA_URL`.

La prueba CU3 crea un pedido real y descuenta una unidad de stock. CU4 envía un
equipo sin recomendaciones y comprueba el `409` definido para ese caso. Un
`404` solo se produce si Decisión devuelve una recomendación obsoleta cuyo ID
ya no existe en Datos.

## CU5: servicio de Datos apagado

CU5 requiere apagar Datos manualmente; no se detiene ningún servicio desde el
test. Deja Puerta y Decisión activos, apaga Datos y ejecuta. El test comprueba
primero que Datos no responda; si sigue activo, avisa y no crea ningún pedido:

```bash
API_KEY="una-clave-local" PROBAR_CU5=1 python -m unittest discover \
  -s tests_integracion -p "test_integracion.py" -v
```

La prueba espera `503` y un mensaje que mencione Datos. Vuelve a arrancar Datos
al terminar.

Las rutas de Puerta tienen un límite de cinco peticiones autenticadas por
minuto y clave. Si una ejecución anterior consumió el límite, espera 60
segundos antes de repetirla.
