import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from backend.app.core.config import settings
from backend.app.api.routes import auth, documents, collections, chat, stats, health, search

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure upload storage directory exists
    os.makedirs(os.path.abspath(settings.STORAGE_DIR), exist_ok=True)
    yield
    # Shutdown

app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise-grade AI Document Research Assistant with verified page citations and pgvector grounding.",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS middleware
origins = settings.CORS_ALLOWED_ORIGINS
if isinstance(origins, str):
    origins = [origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-CSRF-Token"],
)

# Custom Validation Exception Handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0]["msg"] if errors else "Invalid request data"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": first_error, "errors": errors},
    )

# Register API v1 routes
API_PREFIX = "/api/v1"
app.include_router(health.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(documents.router, prefix=API_PREFIX)
app.include_router(collections.router, prefix=API_PREFIX)
app.include_router(chat.router, prefix=API_PREFIX)
app.include_router(search.router, prefix=API_PREFIX)
app.include_router(stats.router, prefix=API_PREFIX)

# Also expose routes at root for resilience and direct domain routing
app.include_router(health.router, prefix="")
app.include_router(auth.router, prefix="")
app.include_router(documents.router, prefix="")
app.include_router(collections.router, prefix="")
app.include_router(chat.router, prefix="")
app.include_router(search.router, prefix="")
app.include_router(stats.router, prefix="")
