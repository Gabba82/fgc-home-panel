# FGC Home Panel

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED)
![License](https://img.shields.io/badge/license-sin%20definir-lightgrey)

Panel web autohospedado para consultar los próximos trenes de FGC entre **Sant Boi** y **Barcelona - Plaça Espanya**.

Pensado para una pantalla de casa, tablet, móvil o navegador siempre abierto. Muestra los próximos trenes en ambos sentidos, se actualiza automáticamente y usa datos públicos de Dades Obertes FGC.

## Tabla de contenidos

- [Características](#características)
- [Captura](#captura)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Uso](#uso)
- [Configuración](#configuración)
- [API](#api)
- [Fuentes de datos](#fuentes-de-datos)
- [Desarrollo](#desarrollo)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Solución de problemas](#solución-de-problemas)
- [Limitaciones](#limitaciones)
- [Licencia](#licencia)

## Características

- Consulta de trenes Sant Boi -> Barcelona - Plaça Espanya.
- Consulta de trenes Barcelona - Plaça Espanya -> Sant Boi.
- Consulta de próximos autobuses AMB en la parada `107214`.
- Horas previstas y estimadas de salida y llegada.
- Estado del tren: en hora, retrasado, cancelado, sin datos en tiempo real o con incidencia.
- Andén y color de línea cuando FGC lo publica.
- Actualización automática cada 30 segundos.
- Frontend responsive en HTML, CSS y JavaScript.
- Backend con FastAPI.
- Despliegue con Docker Compose.
- Sin base de datos.

## Captura

<!-- Añade aquí una captura: `![Panel FGC](docs/screenshot.png)` -->

## Requisitos

- Docker
- Docker Compose

Para desarrollo local sin Docker:

- Python 3.12 o superior

## Instalación

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

- `Sant Boi -> Barcelona - Plaça Espanya`
- `Barcelona - Plaça Espanya -> Sant Boi`

Cada tren muestra la línea, hora de salida, hora de llegada, destino del tren, andén si está disponible y estado del servicio.

Estados posibles:

| Estado | Significado |
| --- | --- |
| `En hora` | Hay datos en tiempo real y no se detecta retraso. |
| `+N min` | Retraso estimado en minutos. |
| `Cancelado` | El tren aparece como cancelado. |
| `Sin datos en tiempo real` | Hay horario previsto, pero no se ha podido cruzar con datos en tiempo real fiables. |
| `Incidencia` | Hay una alerta relevante para la línea, zona o parada. |

`Sin datos en tiempo real` no significa necesariamente que el tren no circule. Significa que la aplicación está mostrando el horario previsto porque no ha encontrado una coincidencia fiable con el feed en tiempo real.

## Comandos útiles

Parar la aplicación:

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

## Configuración

Puedes configurar la aplicación con variables de entorno o con un archivo `.env` junto a `docker-compose.yml`.

Copia el archivo de ejemplo y edítalo:

```bash
cp .env.example .env
```

Ejemplo de `.env`:

```env
FGC_EXTERNAL_PORT=8099
FGC_TIMEZONE=Europe/Madrid
FGC_CACHE_TTL_SECONDS=30
FGC_HTTP_TIMEOUT_SECONDS=8
FGC_LOG_LEVEL=INFO
```

| Variable | Valor por defecto | Descripción |
| --- | --- | --- |
| `FGC_EXTERNAL_PORT` | `8099` | Puerto publicado por Docker. |
| `FGC_TIMEZONE` | `Europe/Madrid` | Zona horaria usada por la aplicación. |
| `FGC_CACHE_TTL_SECONDS` | `30` | Caché en memoria para reducir llamadas a FGC. |
| `FGC_HTTP_TIMEOUT_SECONDS` | `8` | Timeout HTTP al consultar FGC. |
| `FGC_API_BASE_URL` | API de Dades Obertes FGC | URL base de la API de FGC. |
| `FGC_LOG_LEVEL` | `INFO` | Nivel de logs. |
| `FGC_AMB_APP_ID` | `5b1fdf3a` | Identificador de la aplicación en la API TMB/AMB. |
| `FGC_AMB_APP_KEY` | vacío | Clave privada de la API TMB/AMB. Guárdala solo en `.env`. |
| `FGC_BUS_STOP_ID` | `107214` | Parada AMB que se muestra en el panel. |
| `FGC_BUS_STOP_URL` | Web AMB Mobilitat | URL de la ficha de parada AMB. |
| `FGC_BUS_ARRIVALS_LIMIT` | `6` | Número máximo de llegadas de bus a mostrar. |

## API

| Endpoint | Descripción |
| --- | --- |
| `GET /` | Interfaz web. |
| `GET /api/routes` | Sentidos configurados. |
| `GET /api/next-trains?sense=santboi-espanya` | Próximos trenes Sant Boi -> Plaça Espanya. |
| `GET /api/next-trains?sense=espanya-santboi` | Próximos trenes Plaça Espanya -> Sant Boi. |
| `GET /api/alerts` | Alertas relevantes. |
| `GET /api/bus-stop?stop_id=107214` | Próximos autobuses de una parada AMB. |
| `GET /api/health` | Estado de la app y conectividad con FGC. |

## Fuentes de datos

La aplicación consulta Dades Obertes FGC:

```text
https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/
```

Datasets usados:

| Dataset | Uso |
| --- | --- |
| `viajes-de-hoy` | Horarios previstos del día. |
| `trip-updates-gtfs_realtime` | Retrasos, cambios y cancelaciones. |
| `alerts-gtfs_realtime` | Alertas de servicio. |
| `vehicle-positions-gtfs_realtime` | Posiciones de vehículos, usado en `/api/health`. |

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

## Solución de problemas

**El panel carga pero los textos muestran caracteres extraños (`Ã©n`, `Â·`)**

La versión actualizada del código corrige esto de tres maneras: el servidor declara `charset=utf-8` en la respuesta HTTP para archivos JS y CSS, el HTML incluye el atributo `charset="utf-8"` en el tag `<script>`, y Python fuerza la decodificación UTF-8 al leer la API de FGC. Si tras actualizar sigues viendo el problema, fuerza la reconstrucción de la imagen:

```bash
docker compose down
docker compose up -d --build
```

**El panel muestra "No se han podido actualizar los datos"**

Comprueba que el contenedor tiene acceso a internet (el servidor de FGC está en `dadesobertes.fgc.cat`). Revisa los logs con `docker compose logs -f` para ver el error concreto.

**`docker compose up` no recoge los cambios de `.env`**

Ejecuta `docker compose up -d` (sin `--build`) para releer las variables de entorno sin reconstruir la imagen.

## Limitaciones

- El horario base procede de `viajes-de-hoy`, que contiene horarios previstos del día.
- Los feeds GTFS Realtime no siempre se pueden cruzar con precisión perfecta.
- Si no hay cruce fiable con datos en tiempo real, se muestra `Sin datos en tiempo real`.
- Las alertas se filtran por textos relacionados con FGC, Llobregat-Anoia, Sant Boi y Espanya.
- Este panel es una ayuda visual y no sustituye la información oficial de FGC en incidencias importantes.

## Licencia

Licencia no definida por ahora.
