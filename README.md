# FGC Home Panel

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED)
![License](https://img.shields.io/badge/license-sin%20definir-lightgrey)

Panel web autohospedado para consultar los proximos trenes de FGC entre **Sant Boi** y **Barcelona - Placa Espanya**.

Pensado para una pantalla de casa, tablet, movil o navegador siempre abierto. Muestra los proximos trenes en ambos sentidos, se actualiza automaticamente y usa datos publicos de Dades Obertes FGC.

## Tabla de contenidos

- [Caracteristicas](#caracteristicas)
- [Captura](#captura)
- [Requisitos](#requisitos)
- [Instalacion](#instalacion)
- [Uso](#uso)
- [Configuracion](#configuracion)
- [API](#api)
- [Fuentes de datos](#fuentes-de-datos)
- [Desarrollo](#desarrollo)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Limitaciones](#limitaciones)
- [Licencia](#licencia)

## Caracteristicas

- Consulta de trenes Sant Boi -> Barcelona - Placa Espanya.
- Consulta de trenes Barcelona - Placa Espanya -> Sant Boi.
- Consulta de prÃ³ximos autobuses AMB en la parada `107214`.
- Horas previstas y estimadas de salida y llegada.
- Estado del tren: en hora, retrasado, cancelado, sin datos realtime o con incidencia.
- Anden y color de linea cuando FGC lo publica.
- Actualizacion automatica cada 30 segundos.
- Frontend responsive en HTML, CSS y JavaScript.
- Backend con FastAPI.
- Despliegue con Docker Compose.
- Sin base de datos.

## Captura

Pendiente de anadir captura del panel.

## Requisitos

- Docker
- Docker Compose

Para desarrollo local sin Docker:

- Python 3.12 o superior

## Instalacion

Clona el repositorio:

```bash
git clone https://github.com/Gabba82/fgc-home-panel.git
cd fgc-home-panel
```

Arranca el contenedor:

```bash
docker compose up -d --build
```

Abre el panel:

```text
http://localhost:8099
```

Si lo ejecutas en un servidor o Raspberry Pi, cambia `localhost` por la IP del equipo:

```text
http://IP_DEL_SERVIDOR:8099
```

## Uso

El panel muestra dos tarjetas:

- `Sant Boi -> Barcelona - Placa Espanya`
- `Barcelona - Placa Espanya -> Sant Boi`

Cada tren muestra la linea, hora de salida, hora de llegada, destino del tren, anden si esta disponible y estado del servicio.

Estados posibles:

| Estado | Significado |
| --- | --- |
| `En hora` | Hay datos en tiempo real y no se detecta retraso. |
| `+N min` | Retraso estimado en minutos. |
| `Cancelado` | El tren aparece como cancelado. |
| `Sin datos realtime` | Hay horario previsto, pero no se ha podido cruzar con datos en tiempo real fiables. |
| `Incidencia` | Hay una alerta relevante para la linea, zona o parada. |

`Sin datos realtime` no significa necesariamente que el tren no circule. Significa que la aplicacion esta mostrando el horario previsto porque no ha encontrado una coincidencia fiable con el feed realtime.

## Comandos utiles

Parar la aplicacion:

```bash
docker compose down
```

Reconstruir y reiniciar:

```bash
docker compose up -d --build
```

Ver logs:

```bash
docker compose logs -f
```

## Configuracion

Puedes configurar la aplicacion con variables de entorno o con un archivo `.env` junto a `docker-compose.yml`.

Ejemplo:

```env
FGC_EXTERNAL_PORT=8099
FGC_TIMEZONE=Europe/Madrid
FGC_CACHE_TTL_SECONDS=30
FGC_HTTP_TIMEOUT_SECONDS=8
FGC_LOG_LEVEL=INFO
```

| Variable | Valor por defecto | Descripcion |
| --- | --- | --- |
| `FGC_EXTERNAL_PORT` | `8099` | Puerto publicado por Docker. |
| `FGC_TIMEZONE` | `Europe/Madrid` | Zona horaria usada por la aplicacion. |
| `FGC_CACHE_TTL_SECONDS` | `30` | Cache en memoria para reducir llamadas a FGC. |
| `FGC_HTTP_TIMEOUT_SECONDS` | `8` | Timeout HTTP al consultar FGC. |
| `FGC_API_BASE_URL` | API de Dades Obertes FGC | URL base de la API de FGC. |
| `FGC_LOG_LEVEL` | `INFO` | Nivel de logs. |
| `FGC_AMB_APP_ID` | `5b1fdf3a` | Identificador de la aplicacion en la API TMB/AMB. |
| `FGC_AMB_APP_KEY` | vacio | Clave privada de la API TMB/AMB. Guardala solo en `.env`. |
| `FGC_BUS_STOP_ID` | `107214` | Parada AMB que se muestra en el panel. |
| `FGC_BUS_STOP_URL` | Web AMB Mobilitat | URL de la ficha de parada AMB. |
| `FGC_BUS_ARRIVALS_LIMIT` | `6` | NÃºmero mÃ¡ximo de llegadas de bus a mostrar. |

## API

| Endpoint | Descripcion |
| --- | --- |
| `GET /` | Interfaz web. |
| `GET /api/routes` | Sentidos configurados. |
| `GET /api/next-trains?sense=santboi-espanya` | Proximos trenes Sant Boi -> Placa Espanya. |
| `GET /api/next-trains?sense=espanya-santboi` | Proximos trenes Placa Espanya -> Sant Boi. |
| `GET /api/alerts` | Alertas relevantes. |
| `GET /api/bus-stop?stop_id=107214` | PrÃ³ximos autobuses de una parada AMB. |
| `GET /api/health` | Estado de la app y conectividad con FGC. |

## Fuentes de datos

La aplicacion consulta Dades Obertes FGC:

```text
https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/
```

Datasets usados:

| Dataset | Uso |
| --- | --- |
| `viajes-de-hoy` | Horarios previstos del dia. |
| `trip-updates-gtfs_realtime` | Retrasos, cambios y cancelaciones. |
| `alerts-gtfs_realtime` | Alertas de servicio. |
| `vehicle-positions-gtfs_realtime` | Posiciones de vehiculos, usado en `/api/health`. |

## Desarrollo

Crea y activa un entorno virtual:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Instala dependencias:

```bash
pip install -r requirements.txt
```

Arranca el servidor de desarrollo:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Abre:

```text
http://localhost:8000
```

## Estructura del proyecto

```text
fgc-home-panel/
|-- app/
|   |-- static/
|   |   |-- app.js
|   |   |-- index.html
|   |   `-- style.css
|   |-- config.py
|   |-- fgc_client.py
|   |-- main.py
|   |-- models.py
|   `-- services.py
|-- docker-compose.yml
|-- Dockerfile
|-- requirements.txt
`-- README.md
```

## Limitaciones

- El horario base procede de `viajes-de-hoy`, que contiene horarios previstos del dia.
- Los feeds GTFS Realtime no siempre se pueden cruzar con precision perfecta.
- Si no hay cruce fiable con realtime, se muestra `Sin datos realtime`.
- Las alertas se filtran por textos relacionados con FGC, Llobregat-Anoia, Sant Boi y Espanya.
- Este panel es una ayuda visual y no sustituye la informacion oficial de FGC en incidencias importantes.

## Licencia

Licencia no definida por ahora.
