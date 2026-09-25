from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.middleware import protection_middleware
from backend.app.scheduler.runtime import scheduler
from backend.app.api.routes import (
    health, standards, services, faqs, licenses, resources, auth, chat, search, ops, documents, graph, certification_applications, research, feedback
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s operation=%(message)s",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await scheduler.start()
    try:
        yield
    finally:
        await scheduler.stop()

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend for the ManakMitra BIS/Indian-Standards assistant.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware,
    allow_origins=["*"] if "*" in settings.CORS_ORIGINS else settings.CORS_ORIGINS,
    allow_credentials="*" not in settings.CORS_ORIGINS,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.middleware("http")(protection_middleware)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.getLogger(__name__).exception(
        "operation=http_exception success=false error_category=internal_server_error"
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

app.include_router(health.router)
app.include_router(search.router)
app.include_router(standards.router)
app.include_router(services.router)
app.include_router(faqs.router)
app.include_router(resources.router)
app.include_router(licenses.router)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(ops.router)
app.include_router(documents.router)
app.include_router(graph.router)
app.include_router(certification_applications.router)
app.include_router(research.router)
app.include_router(feedback.router)
