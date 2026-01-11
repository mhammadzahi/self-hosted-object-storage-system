"""
Main FastAPI application with production-ready configuration.
Implements a self-hosted object storage system (S3 alternative).
"""
from datetime import datetime
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.exceptions import (
    StorageException,
    BucketNotFoundError,
    BucketAlreadyExistsError,
    ObjectNotFoundError,
    InvalidPathError,
    FileSizeLimitExceededError,
)
from app.routers import buckets, objects
from app.schemas import HealthCheck


# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Self-hosted object storage system - AWS S3 alternative with local filesystem backend",
    docs_url="/docs",
    redoc_url="/redoc",
)


# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)


# Global exception handlers
@app.exception_handler(BucketNotFoundError)
async def bucket_not_found_handler(request: Request, exc: BucketNotFoundError):
    """Handle bucket not found exceptions."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": "BucketNotFound", "detail": str(exc), "code": "NoSuchBucket"}
    )


@app.exception_handler(BucketAlreadyExistsError)
async def bucket_already_exists_handler(request: Request, exc: BucketAlreadyExistsError):
    """Handle bucket already exists exceptions."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"error": "BucketAlreadyExists", "detail": str(exc), "code": "BucketAlreadyOwnedByYou"}
    )


@app.exception_handler(ObjectNotFoundError)
async def object_not_found_handler(request: Request, exc: ObjectNotFoundError):
    """Handle object not found exceptions."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": "ObjectNotFound", "detail": str(exc), "code": "NoSuchKey"}
    )


@app.exception_handler(InvalidPathError)
async def invalid_path_handler(request: Request, exc: InvalidPathError):
    """Handle invalid path exceptions (path traversal attempts)."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "InvalidPath", "detail": "Invalid or unsafe path detected", "code": "InvalidRequest"}
    )


@app.exception_handler(FileSizeLimitExceededError)
async def file_size_limit_handler(request: Request, exc: FileSizeLimitExceededError):
    """Handle file size limit exceeded exceptions."""
    return JSONResponse(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        content={
            "error": "EntityTooLarge",
            "detail": str(exc),
            "code": "EntityTooLarge",
            "max_size": exc.max_size
        }
    )


@app.exception_handler(StorageException)
async def storage_exception_handler(request: Request, exc: StorageException):
    """Handle generic storage exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "StorageError", "detail": str(exc), "code": "InternalError"}
    )


# Include routers
app.include_router(buckets.router, prefix="/api/v1")
app.include_router(objects.router, prefix="/api/v1")


# Root endpoints
@app.get(
    "/",
    response_model=HealthCheck,
    tags=["Health"],
    summary="Health check",
    description="Returns service health status and configuration information."
)
async def root():
    """Root endpoint with health check."""
    return HealthCheck(
        status="healthy",
        version=settings.app_version,
        storage_backend=settings.storage_backend,
        timestamp=datetime.now()
    )


@app.get(
    "/health",
    response_model=HealthCheck,
    tags=["Health"],
    summary="Health check",
    description="Health check endpoint for monitoring and load balancers."
)
async def health_check():
    """Health check endpoint."""
    return HealthCheck(
        status="healthy",
        version=settings.app_version,
        storage_backend=settings.storage_backend,
        timestamp=datetime.now()
    )


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    print(f"🚀 {settings.app_name} v{settings.app_version} starting...")
    print(f"📦 Storage backend: {settings.storage_backend}")
    print(f"📁 Storage path: {settings.get_storage_path()}")
    print(f"🔒 Path traversal protection: {settings.enable_path_traversal_protection}")
    print(f"📏 Max file size: {settings.max_file_size / (1024*1024*1024):.2f} GB")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    print(f"👋 {settings.app_name} shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info",
        access_log=True
    )

