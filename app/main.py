import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from .amb_client import AMBClient
from .config import get_settings
from .fgc_client import FGCClient
from .models import BusStopResponse, HealthResponse, NextTrainsResponse, RouteSense
from .services import FGCService, now_local

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = FGCClient(settings)
    amb_client = AMBClient(settings)
    app.state.fgc_client = client
    app.state.amb_client = amb_client
    app.state.fgc_service = FGCService(client, settings)
    logger.info("FGC Home Panel started timezone=%s cache_ttl=%ss", settings.timezone, settings.cache_ttl_seconds)
    try:
        yield
    finally:
        await client.close()
        await amb_client.close()


class _TextAssetsCharset(BaseHTTPMiddleware):
    """Ensures JS and CSS static files are served with charset=utf-8."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        ct = response.headers.get("content-type", "")
        if ("javascript" in ct or "text/css" in ct) and "charset" not in ct:
            response.headers["content-type"] = ct + "; charset=utf-8"
        return response


app = FastAPI(title="FGC Home Panel", version="1.0.0", lifespan=lifespan)
app.add_middleware(_TextAssetsCharset)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.get("/api/routes", response_model=list[RouteSense])
async def routes() -> list[RouteSense]:
    return app.state.fgc_service.routes()


@app.get("/api/next-trains", response_model=NextTrainsResponse)
async def next_trains(
    sense: str = Query(..., pattern="^(santboi-espanya|espanya-santboi)$"),
) -> NextTrainsResponse:
    try:
        return await app.state.fgc_service.next_trains(sense)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Could not build next trains response")
        raise HTTPException(status_code=503, detail="No se han podido consultar los horarios de FGC") from exc


@app.get("/api/alerts")
async def alerts():
    return {"updated_at": now_local(settings).isoformat(), "alerts": await app.state.fgc_service.alerts()}


@app.get("/api/bus-stop", response_model=BusStopResponse)
async def bus_stop(stop_id: str = Query(default=settings.bus_stop_id, pattern=r"^\d+$")) -> BusStopResponse:
    try:
        return await app.state.amb_client.stop_arrivals(stop_id)
    except Exception as exc:
        logger.exception("Could not read AMB bus stop %s", stop_id)
        raise HTTPException(status_code=503, detail="No se han podido consultar los autobuses de AMB") from exc


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    current = now_local(settings).isoformat()
    try:
        await app.state.fgc_client.ping()
        vehicles = await app.state.fgc_service.vehicle_positions_summary()
        detail = f"FGC API reachable. Vehicle positions: {vehicles.get('vehicles', 0)} active records."
        return HealthResponse(status="ok", fgc_api="ok", updated_at=current, detail=detail)
    except Exception as exc:
        logger.warning("Health check degraded: %s", exc)
        return HealthResponse(status="degraded", fgc_api="error", updated_at=current, detail=str(exc))
