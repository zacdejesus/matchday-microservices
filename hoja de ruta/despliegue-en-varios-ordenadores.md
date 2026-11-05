# Hoja de ruta: ejecutar los servicios en ordenadores distintos

Esta guía explica cómo ejecutar **Datos**, **Decisión** y **Puerta** en tres
ordenadores de la misma red local y cómo conectar el panel de pruebas con ellos.
Los ejemplos usan direcciones privadas ficticias: sustitúyelas por las IP reales
de vuestra red.

> **Importante:** esto es una configuración de desarrollo para una red local
> de confianza, no una publicación en Internet. No abras estos puertos en el
> router ni expongas los servicios a Internet. La API key de Puerta viaja por
> HTTP sin cifrar.

## 1. Decidir qué ordenador ejecuta cada servicio

Anota la dirección IPv4 de cada ordenador. Es preferible reservar las IP desde
el router para que no cambien después de reiniciar.

| Ordenador | Servicio | IP de ejemplo | Puerto |
|---|---|---:|---:|
| PC Datos | Django / Datos | `192.168.1.20` | `8001` |
| PC Decisión | FastAPI / Decisión | `192.168.1.30` | `8002` |
| PC Puerta | Flask / Puerta | `192.168.1.40` | `8000` |
| PC Panel (puede ser cualquiera) | Panel y tienda | `192.168.1.50` | `8080` |

Usa las IP que tengan sentido en vuestra red. No copies las de ejemplo sin
comprobarlas: los ordenadores deben estar conectados a la misma LAN o Wi-Fi y
poder comunicarse entre sí.

### Averiguar la IP

- **Linux:** ejecuta `hostname -I` y localiza la IP de la red local
  (normalmente empieza por `192.168.`, `10.` o `172.16`–`172.31`).
- **Windows:** ejecuta `ipconfig` en PowerShell o CMD y busca la «Dirección
  IPv4» del adaptador Wi-Fi o Ethernet activo.
- **WSL 2:** si usa NAT, `hostname -I` suele mostrar la IP interna de WSL, no
  una IP que los demás ordenadores de la LAN puedan usar. Anota la IP LAN de
  Windows con `ipconfig` y consulta la sección de WSL 2 más abajo para configurar
  el acceso entrante.
- No uses `127.0.0.1` ni `localhost` como dirección de otro ordenador: esas
  direcciones siempre apuntan al propio ordenador.

## 2. Preparación común en cada ordenador

1. Clona el repositorio en cada PC y entra en la carpeta
   `matchday-microservices`.
2. Instala Python y las dependencias del servicio que se ejecutará en ese PC.
   Se pueden usar entornos virtuales independientes.
3. Comprueba que la IP de cada PC no cambia. Si cambia, actualiza las variables
   de entorno del resto de servicios que apuntan a ese PC.
4. Permite conexiones entrantes **solo desde vuestra LAN** en el firewall:
   TCP `8001` en el PC Datos, TCP `8002` en el PC Decisión y TCP `8000` en el PC
   Puerta. El PC Panel solo necesita el puerto `8080` si otras personas de la
   LAN van a abrir el panel desde sus navegadores.

En Ubuntu con `ufw`, un ejemplo para permitir Datos solo desde una subred
`192.168.1.0/24` es:

```bash
sudo ufw allow from 192.168.1.0/24 to any port 8001 proto tcp
```

En el PC Decisión usa el puerto `8002`; en el PC Puerta, `8000`. Sustituye la
subred por la que realmente use vuestro router. En Windows, crea una regla
entrante equivalente para el puerto correspondiente y limita el perfil a
**Privado** y, si es posible, el ámbito remoto a vuestra subred.

### Si Python se ejecuta dentro de WSL 2

Los comandos de arranque de esta guía escuchan en `0.0.0.0`, pero eso por sí
solo no garantiza que otros ordenadores de la LAN puedan alcanzar un servicio
de WSL 2 con red NAT. La IP interna de WSL suele ser distinta de la IP LAN de
Windows y puede cambiar.

- En Windows 11 con una versión de WSL compatible, se puede configurar el modo
  de red **mirrored** de WSL 2. Comprueba la documentación de WSL de ese equipo
  y las reglas de Windows Firewall; después prueba el acceso desde otro PC.
- Si se mantiene el modo NAT, hay que configurar en Windows un reenvío del
  puerto LAN al IP actual de WSL, además de una regla de Firewall limitada a la
  red privada. Ese IP puede cambiar al reiniciar WSL, por lo que habrá que
  actualizar el reenvío y probarlo de nuevo.
- Si no podéis confirmar conectividad entrante desde la LAN, no asumáis que
  funciona por ver el servicio en `localhost`: probadlo desde otro ordenador
  antes de configurar los servicios que dependen de él.

## 3. PC Datos: publicar Django en la LAN

En `datos/datos/settings.py`, Django tiene `ALLOWED_HOSTS = []`. Añade la IP
LAN del PC Datos como host permitido. Por ejemplo, si su IP es
`192.168.1.20`:

```python
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "192.168.1.20"]
```

No escribas `http://` ni el puerto dentro de `ALLOWED_HOSTS`; solo el nombre o
la IP. Si la IP cambia, actualiza esta lista.

En el PC Datos, desde la raíz del repositorio:

```bash
cd datos
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8001
```

`0.0.0.0` hace que el servidor de desarrollo escuche en las interfaces de red
del PC, no solo en `localhost`. No uses el servidor de desarrollo de Django
para una publicación en Internet.

Desde otro PC de la misma red, prueba:

```bash
curl -i http://192.168.1.20:8001/equipaciones
```

Debe responder con HTTP `200` y una lista JSON. Si recibes «DisallowedHost»,
revisa `ALLOWED_HOSTS`; si no hay conexión, revisa IP, firewall y red de WSL.

## 4. PC Decisión: conectar FastAPI con Datos

Decisión debe conocer la IP del PC Datos. En una terminal del PC Decisión,
desde la carpeta `decision`, sustituye `192.168.1.20` por la IP real:

```bash
cd decision
python -m pip install -r requirements.txt
DATA_URL=http://192.168.1.20:8001 uvicorn main:app --host 0.0.0.0 --port 8002
```

En PowerShell, la sintaxis de variable de entorno es distinta:

```powershell
cd decision
$env:DATA_URL = "http://192.168.1.20:8001"
python -m pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8002
```

Comprueba desde otro PC que Decisión es accesible:

```bash
curl -i http://192.168.1.30:8002/salud
```

Debe responder HTTP `200` con `{"estado":"ok"}`. Para comprobar también que
Decisión alcanza a Datos, envía una petición a `/recomendar`:

```bash
curl -i -X POST http://192.168.1.30:8002/recomendar \
  -H 'Content-Type: application/json' \
  -d '{"equipo":"Betis","presupuesto":100,"talla":"M"}'
```

## 5. PC Puerta: conectar Flask con Decisión y Datos

Puerta necesita las IP de **ambos** servicios. Define las variables en la misma
terminal en la que inicias Flask; si cierras esa terminal, tendrás que volver a
definirlas.

En Linux o WSL, desde `puerta`:

```bash
cd puerta
python -m pip install -r requirements.txt
DECISION_URL=http://192.168.1.30:8002 \
DATA_URL=http://192.168.1.20:8001 \
API_KEY='cambia-esto-por-una-clave-local' \
python app.py
```

En PowerShell:

```powershell
cd puerta
$env:DECISION_URL = "http://192.168.1.30:8002"
$env:DATA_URL = "http://192.168.1.20:8001"
$env:API_KEY = "cambia-esto-por-una-clave-local"
python -m pip install -r requirements.txt
python app.py
```

`app.py` ya inicia Flask escuchando en `0.0.0.0:8000`. Guarda la API key en
privado y usa exactamente la misma en el panel o en las peticiones de prueba.
No publiques una clave real en Git.

Desde otro ordenador, comprueba que Puerta responde:

```bash
curl -i http://192.168.1.40:8000/pedidos \
  -H 'X-API-Key: cambia-esto-por-una-clave-local'
```

Una respuesta HTTP `200` indica que la clave es válida. `401` significa que
falta o no coincide; `429` significa que se ha alcanzado el límite temporal.

## 6. PC Panel: conectar el panel y la tienda a los tres servicios

El panel reenvía las peticiones desde su servidor Python, así que configura
allí las direcciones LAN de los tres servicios. No cambies las URL de las
peticiones del navegador a `localhost`: el reenvío lo hace `front/servidor.py`.

En Linux o WSL, desde la raíz del repositorio:

```bash
DATA_URL=http://192.168.1.20:8001 \
DECISION_URL=http://192.168.1.30:8002 \
PUERTA_URL=http://192.168.1.40:8000 \
python front/servidor.py
```

En PowerShell:

```powershell
$env:DATA_URL = "http://192.168.1.20:8001"
$env:DECISION_URL = "http://192.168.1.30:8002"
$env:PUERTA_URL = "http://192.168.1.40:8000"
python front/servidor.py
```

Abre `http://localhost:8080/panel` en el navegador del mismo PC Panel. Escribe
en **X-API-Key** exactamente la clave configurada al iniciar Puerta, pulsa
**Comprobar API key** y después **Comprobar servicios**. El campo se usa para
las pruebas que atraviesan Puerta; las llamadas directas a Datos y Decisión no
necesitan esa clave.

El servidor del panel escucha actualmente solo en `127.0.0.1:8080`. Por eso,
por defecto, el panel se abre desde el mismo ordenador en el que se inició. Si
se necesita abrir desde otros ordenadores, habría que cambiar el servidor del
panel y limitar su acceso con el firewall; no es necesario para que los tres
servicios se comuniquen.

## 7. Orden recomendado de arranque y prueba completa

Deja una terminal abierta por cada servicio:

1. **Datos**, en su ordenador; confirma `GET /equipaciones` desde otro PC.
2. **Decisión**, con `DATA_URL` apuntando al PC Datos; confirma `/salud` y
   prueba `/recomendar`.
3. **Puerta**, con `DATA_URL` y `DECISION_URL` apuntando a sus respectivos PCs;
   prueba `GET /pedidos` con `X-API-Key`.
4. **Panel**, con las tres URL configuradas; comprueba el estado de los servicios
   y ejecuta las pruebas.
5. Si un servicio no responde, verifica en este orden: IP correcta, proceso
   escuchando en `0.0.0.0` y puerto indicado, firewall LAN, conectividad de
   WSL/Windows y variables de entorno del servicio que lo consume.

### Tabla de direcciones que hay que sustituir

Antes de arrancar, reemplaza cada IP de ejemplo por la IP real:

```text
IP_DATOS    = IP del PC Datos
IP_DECISION = IP del PC Decisión
IP_PUERTA   = IP del PC Puerta

Decisión: DATA_URL=http://IP_DATOS:8001
Puerta:   DATA_URL=http://IP_DATOS:8001
          DECISION_URL=http://IP_DECISION:8002
Panel:    DATA_URL=http://IP_DATOS:8001
          DECISION_URL=http://IP_DECISION:8002
          PUERTA_URL=http://IP_PUERTA:8000
```

## 8. Límites actuales que conviene conocer

- El servicio Datos mantiene el catálogo en la lista `EQUIPACIONES` de
  `datos/equipaciones/views.py`; en este estado del proyecto no lo guarda en
  SQLite. Los cambios de catálogo o stock hechos durante la ejecución se
  reinician al apagar el proceso.
- Puerta guarda los pedidos en memoria. Al reiniciarla, la lista de pedidos se
  reinicia.
- Si el PC Datos o el PC Decisión está apagado o cambia de IP, los servicios
  que dependan de él devolverán errores hasta restaurar la conexión o actualizar
  la URL configurada.






<!-- si yo le paso este archivo a una ia con las diferentes direcciones ips lo onfigurar tienedo en cuenta que la ip de red es la misma

11:16 PM
Sí. Puedes pasarle la guía a una IA junto con las IP reales para que adapte los comandos y la configuración.

Solo una precisión: los ordenadores deben compartir la misma red, pero cada uno necesita una IP distinta. Por ejemplo:

PC Datos: 192.168.1.20
PC Decisión: 192.168.1.30
PC Puerta: 192.168.1.40
Comparten el prefijo 192.168.1, pero no pueden tener la misma IP. Para que la IA lo configure bien, indícale también la máscara o subred (por ejemplo, 192.168.1.0/24) y si cada servicio correrá en Windows, Linux o WSL 2. No incluyas una API key real; usa un marcador y configúrala localmente. -->