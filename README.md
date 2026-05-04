# FGC Home Panel

A small self-hosted web panel for checking the next FGC trains between **Sant Boi** and **Barcelona - Placa Espanya**.

The app is designed for a home dashboard, tablet, phone, or browser tab. It shows upcoming trains in both directions, refreshes automatically, and uses public data from Dades Obertes FGC.

## Features

- Upcoming trains from Sant Boi to Barcelona - Placa Espanya.
- Upcoming trains from Barcelona - Placa Espanya to Sant Boi.
- Scheduled and estimated departure and arrival times.
- FGC line badge and route colors when available.
- Platform information when published by FGC.
- Delay, cancellation, realtime availability, and service-alert states.
- Automatic refresh every 30 seconds.
- Docker-based deployment.
- No database required.

## Preview

The home screen contains two route cards:

- `Sant Boi -> Barcelona - Placa Espanya`
- `Barcelona - Placa Espanya -> Sant Boi`

Each train row shows the line, departure time, arrival time, destination/headsign, platform, and current status.

## Tech Stack

- [FastAPI](https://fastapi.tiangolo.com/)
- HTML, CSS, and JavaScript
- Docker and Docker Compose
- Dades Obertes FGC
- GTFS Realtime protobuf feeds

## Requirements

For the recommended setup:

- Docker
- Docker Compose

For local development without Docker:

- Python 3.12+

## Quick Start

Clone the repository:

```bash
git clone https://github.com/Gabba82/fgc-home-panel.git
cd fgc-home-panel
```

Start the app:

```bash
docker compose up -d --build
```

Open the panel:

```text
http://localhost:8099
```

If it is running on another machine, replace `localhost` with the server IP:

```text
http://IP_DEL_SERVIDOR:8099
```

## Docker Commands

Stop the app:

```bash
docker compose down
```

Rebuild and restart:

```bash
docker compose up -d --build
```

View logs:

```bash
docker compose logs -f
```

## Configuration

Configuration can be provided with environment variables or an `.env` file next to `docker-compose.yml`.

Example `.env`:

```env
FGC_EXTERNAL_PORT=8099
FGC_TIMEZONE=Europe/Madrid
FGC_CACHE_TTL_SECONDS=30
FGC_HTTP_TIMEOUT_SECONDS=8
FGC_LOG_LEVEL=INFO
```

| Variable | Default | Description |
| --- | --- | --- |
| `FGC_EXTERNAL_PORT` | `8099` | Host port exposed by Docker. |
| `FGC_TIMEZONE` | `Europe/Madrid` | Local timezone used for date and time calculations. |
| `FGC_CACHE_TTL_SECONDS` | `30` | In-memory cache duration to avoid excessive API calls. |
| `FGC_HTTP_TIMEOUT_SECONDS` | `8` | HTTP timeout for FGC requests. |
| `FGC_API_BASE_URL` | FGC open data API URL | Base URL for Dades Obertes FGC. |
| `FGC_LOG_LEVEL` | `INFO` | Application log level. |

## Reading the Panel

Train statuses are displayed as short labels:

| Status | Meaning |
| --- | --- |
| `En hora` | Realtime data is available and no delay was detected. |
| `+N min` | Estimated delay in minutes. |
| `Cancelado` | The train appears as cancelled in realtime data. |
| `Sin datos realtime` | The schedule is available, but no reliable realtime match was found. |
| `Incidencia` | A relevant service alert was found for the route or area. |

`Sin datos realtime` does not necessarily mean the train is not running. It means the app is showing the scheduled time because it could not safely match the train with realtime data.

## API

| Endpoint | Description |
| --- | --- |
| `GET /` | Web interface. |
| `GET /api/routes` | Configured route directions. |
| `GET /api/next-trains?sense=santboi-espanya` | Next trains from Sant Boi to Placa Espanya. |
| `GET /api/next-trains?sense=espanya-santboi` | Next trains from Placa Espanya to Sant Boi. |
| `GET /api/alerts` | Relevant service alerts. |
| `GET /api/health` | App health and FGC connectivity status. |

## Data Sources

Base API:

```text
https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/
```

Datasets:

| Dataset | Use |
| --- | --- |
| `viajes-de-hoy` | Scheduled trips for the current day. |
| `trip-updates-gtfs_realtime` | Realtime delays, changes, and cancellations. |
| `alerts-gtfs_realtime` | Service alerts. |
| `vehicle-positions-gtfs_realtime` | Vehicle positions, currently used by the health check. |

## Matching Logic

Some useful trains do not have Sant Boi or Placa Espanya as their final destination. For example, trains toward Martorell, Olesa, Manresa, Igualada, Moli Nou, or Can Ros may still be valid for one of the configured trips.

Because of that, the app does not rely only on the visible train destination. For each future departure from the origin stop, it looks for a later destination stop using:

- `route_short_name`
- `shape_id`
- `trip_headsign`
- later `stop_sequence`
- a reasonable travel-time window

This provides a practical match even when the user destination is an intermediate stop.

## Local Development

Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the development server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000
```

## Project Structure

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

## Known Limitations

- The base schedule comes from `viajes-de-hoy`, which contains planned trips for the day.
- GTFS Realtime feeds are matched against scheduled data, but the match is not always perfect.
- When realtime matching is not reliable, the panel shows `Sin datos realtime`.
- Alerts are filtered by text related to FGC, Llobregat-Anoia, Sant Boi, and Espanya.
- This panel is a convenience dashboard and does not replace official FGC information during major incidents.

## License

No license has been defined yet.
