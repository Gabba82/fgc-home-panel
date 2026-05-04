# FGC Home Panel

Panel web sencillo para ver desde casa los proximos trenes de FGC entre Sant Boi y Barcelona - Placa Espanya.

Esta pensado para abrirlo en una tablet, movil, pantalla domestica o navegador del ordenador y consultar rapidamente:

- Proximos trenes de Sant Boi a Barcelona - Placa Espanya.
- Proximos trenes de Barcelona - Placa Espanya a Sant Boi.
- Hora prevista de salida y llegada.
- Linea del tren.
- Anden, si FGC lo publica.
- Retrasos, cancelaciones o incidencias cuando hay datos disponibles.

La aplicacion usa FastAPI, un frontend HTML/CSS/JavaScript y Docker. No necesita base de datos.

## Que se ve en el panel

La pantalla principal muestra dos tarjetas:

- **Sant Boi -> Barcelona - Placa Espanya**
- **Barcelona - Placa Espanya -> Sant Boi**

En cada tarjeta aparecen los siguientes trenes disponibles. Cada tren incluye:

- **Linea**: por ejemplo S4, S8, R5 o R6, segun el dato publicado por FGC.
- **Hora grande**: hora estimada de salida. Si no hay dato en tiempo real, se muestra la hora programada.
- **Llegada**: hora prevista o estimada de llegada al destino de la tarjeta.
- **Destino del tren**: puede no coincidir con tu parada final. Por ejemplo, un tren hacia Manresa, Igualada, Martorell u Olesa puede pasar igualmente por Sant Boi o Placa Espanya.
- **Anden**: solo aparece si la informacion esta disponible.
- **Estado**: resumen de puntualidad o incidencia.

El panel se actualiza automaticamente cada 30 segundos. Tambien puedes pulsar **Refrescar** para actualizarlo al momento.

## Como interpretar los estados

- **En hora**: FGC publica informacion en tiempo real y no se detecta retraso.
- **+N min**: el tren tiene un retraso estimado de N minutos.
- **Cancelado**: el tren aparece como cancelado en los datos en tiempo real.
- **Sin datos realtime**: hay horario programado, pero no se ha podido cruzar con datos en tiempo real fiables.
- **Incidencia**: hay una alerta relevante de servicio para la linea, zona o parada.

Importante: si aparece **Sin datos realtime**, no significa necesariamente que el tren no circule. Significa que la aplicacion no ha encontrado una confirmacion fiable en los datos en tiempo real de FGC y muestra el horario previsto.

## Instalacion rapida con Docker

Necesitas tener Docker instalado en el equipo o servidor donde quieras ejecutar el panel.

1. Descarga o clona este repositorio.

```bash
git clone https://github.com/Gabba82/fgc-home-panel.git
cd fgc-home-panel
```

2. Arranca la aplicacion.

```bash
docker compose up -d --build
```

3. Abre el panel en el navegador.

```text
http://IP_DEL_SERVIDOR:8099
```

Si lo estas ejecutando en el mismo ordenador, normalmente sera:

```text
http://localhost:8099
```

## Parar o reiniciar

Para parar el panel:

```bash
docker compose down
```

Para reiniciarlo despues de cambiar algo:

```bash
docker compose up -d --build
```

Para ver los logs:

```bash
docker compose logs -f
```

## Configuracion

La configuracion se puede cambiar con variables de entorno o creando un archivo `.env` junto al `docker-compose.yml`.

Ejemplo de `.env`:

```env
FGC_EXTERNAL_PORT=8099
FGC_TIMEZONE=Europe/Madrid
FGC_CACHE_TTL_SECONDS=30
FGC_HTTP_TIMEOUT_SECONDS=8
FGC_LOG_LEVEL=INFO
```

Variables disponibles:

- `FGC_EXTERNAL_PORT`: puerto publicado por Docker. Por defecto `8099`.
- `FGC_TIMEZONE`: zona horaria local. Por defecto `Europe/Madrid`.
- `FGC_CACHE_TTL_SECONDS`: segundos de cache en memoria para no consultar FGC en exceso. Por defecto `30`.
- `FGC_HTTP_TIMEOUT_SECONDS`: tiempo maximo de espera al consultar FGC. Por defecto `8`.
- `FGC_API_BASE_URL`: URL base de la API de Dades Obertes FGC.
- `FGC_LOG_LEVEL`: nivel de logs. Por defecto `INFO`.

## Endpoints utiles

La interfaz web esta en:

```text
GET /
```

La API interna ofrece:

- `GET /api/routes`: sentidos configurados.
- `GET /api/next-trains?sense=santboi-espanya`: proximos trenes Sant Boi -> Placa Espanya.
- `GET /api/next-trains?sense=espanya-santboi`: proximos trenes Placa Espanya -> Sant Boi.
- `GET /api/alerts`: alertas relevantes.
- `GET /api/health`: estado de la aplicacion y conectividad con FGC.

## Datos que usa

La aplicacion consulta Dades Obertes FGC:

```text
https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/
```

Datasets principales:

- `viajes-de-hoy`: horarios previstos del dia.
- `trip-updates-gtfs_realtime`: retrasos, cambios y cancelaciones en GTFS Realtime.
- `alerts-gtfs_realtime`: alertas de servicio en GTFS Realtime.
- `vehicle-positions-gtfs_realtime`: posiciones de vehiculos en GTFS Realtime, consultado en `/api/health`.

## Como decide que tren sirve

FGC publica muchos trenes cuyo destino final no es exactamente Sant Boi o Placa Espanya. Por ejemplo, un tren puede ir a Martorell, Olesa, Manresa, Igualada o Moli Nou y aun asi pasar por una de estas paradas.

Por eso la aplicacion no mira solo el destino escrito en el tren. Para cada salida futura del origen busca una llegada posterior al destino usando:

- Linea.
- Forma del recorrido.
- Nombre de destino del viaje.
- Orden de paradas.
- Ventana de tiempo razonable entre salida y llegada.

Asi puede detectar trenes utiles aunque tu parada sea intermedia.

## Limitaciones conocidas

- El horario base viene de `viajes-de-hoy`, que es el horario previsto del dia.
- Los datos en tiempo real llegan en formato GTFS Realtime y no siempre se pueden cruzar con precision perfecta.
- Si no hay coincidencia fiable con tiempo real, el panel muestra el estado **Sin datos realtime**.
- Las alertas se filtran por textos relacionados con FGC, Llobregat-Anoia, Sant Boi y Espanya.
- La aplicacion no sustituye la informacion oficial de FGC en situaciones criticas o de servicio excepcional.

## Desarrollo local sin Docker

Si quieres ejecutarlo directamente con Python:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Despues abre:

```text
http://localhost:8000
```
