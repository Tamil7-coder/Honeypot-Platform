import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging_config import configure_logging, get_logger
from app.core.rate_limit import limiter
from app.services.connection_manager import connection_manager

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Bind the running event loop so background-thread code (AlertService,
    # which does blocking SMTP I/O in a threadpool) can safely schedule
    # WebSocket broadcasts back onto it via run_coroutine_threadsafe.
    connection_manager.bind_loop(asyncio.get_running_loop())
    logger.info("%s started in %s mode", settings.PROJECT_NAME, settings.ENVIRONMENT)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Enterprise honeypot attack analytics platform - REST API",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Too many requests. Please try again later."},
    )


@app.get("/")
def root():
    return {"service": settings.PROJECT_NAME, "status": "running"}


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
