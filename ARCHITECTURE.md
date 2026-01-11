# Architecture & Design Decisions

## Overview
This document explains the architectural decisions and design patterns used in refactoring the object storage system.

## Project Structure

### Before (Simple Structure)
```
app/
├── config.py          # Basic configuration
├── main.py            # All endpoints in one file
└── storage.py         # Basic file operations
```

### After (Production-Ready Structure)
```
app/
├── __init__.py        # Package initialization
├── config.py          # Environment-based configuration with Pydantic
├── schemas.py         # Request/response models
├── exceptions.py      # Custom exceptions & HTTP handlers
├── storage.py         # Abstract storage backend with local filesystem impl
├── main.py            # Application setup, middleware, error handlers
└── routers/
    ├── __init__.py
    ├── buckets.py     # Bucket management endpoints
    └── objects.py     # Object storage endpoints
```

## Key Improvements

### 1. Configuration Management
**Before:**
```python
import os
UPLOAD_DIR = "UPLOAD_DIR"
os.makedirs(UPLOAD_DIR, exist_ok=True)
```

**After:**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    storage_backend: str = "local"
    storage_base_path: str = "UPLOAD_DIR"
    max_file_size: int = 5 * 1024 * 1024 * 1024
    # ... environment-based configuration with validation
```

**Benefits:**
- Environment variable support with `.env` files
- Type validation and coercion
- Clear documentation of all settings
- Easy to extend for different environments (dev/staging/prod)

### 2. API Structure

**Before:**
```python
@app.post("/upload/")
async def upload_file(file: UploadFile, folder: str = ""):
    file_id = save_file(file, folder)
    return {"file_id": file_id}

@app.get("/download/{file_id}")
async def download_file(file_id: str, folder: str = ""):
    # ...
```

**After:**
```python
# Routers with clear resource hierarchy
/api/v1/buckets/              # Bucket operations
  POST   /                    # Create bucket
  GET    /                    # List buckets
  GET    /{name}              # Get bucket info
  DELETE /{name}              # Delete bucket

/api/v1/objects/              # Object operations
  POST   /{bucket}            # Upload object
  GET    /{bucket}            # List objects
  GET    /{bucket}/{key}      # Download object
  HEAD   /{bucket}/{key}      # Get metadata
  DELETE /{bucket}/{key}      # Delete object
```

**Benefits:**
- RESTful design following S3-like conventions
- Versioned API (`/api/v1/`)
- Clear resource hierarchy
- Standard HTTP methods and status codes

### 3. Storage Abstraction

**Before:**
```python
def save_file(file: UploadFile, folder: str = "") -> str:
    # Direct file operations
    file_path = os.path.join(UPLOAD_DIR, folder, file_id)
    with open(file_path, "wb") as f:
        f.write(file.file.read())  # Loads entire file in memory!
```

**After:**
```python
class StorageBackend(ABC):
    """Abstract base for storage backends"""
    @abstractmethod
    async def put_object(self, bucket, key, file): ...
    @abstractmethod
    async def get_object(self, bucket, key): ...
    # ... other operations

class LocalFilesystemBackend(StorageBackend):
    """Concrete implementation with streaming"""
    async def put_object(self, bucket, key, file):
        # Streams file in chunks
        async with aiofiles.open(object_path, "wb") as f:
            while chunk := await file.read(self.chunk_size):
                await f.write(chunk)
```

**Benefits:**
- Abstract interface allows future backends (S3, MinIO, GCS)
- Streaming operations for memory efficiency
- Async I/O for better concurrency
- Separation of storage logic from API logic

### 4. Security Enhancements

**Path Traversal Protection:**
```python
def _validate_bucket_name(self, bucket: str) -> str:
    """Prevent directory traversal attacks"""
    if not bucket or ".." in bucket or "/" in bucket:
        raise InvalidPathError(bucket)
    return bucket.lower()

def _get_bucket_path(self, bucket: str) -> Path:
    """Ensure path is within storage directory"""
    bucket_path = self.base_path / bucket
    resolved = bucket_path.resolve()
    if not str(resolved).startswith(str(self.base_path.resolve())):
        raise InvalidPathError(bucket)
    return bucket_path
```

**Input Validation:**
```python
class BucketCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=63)
    
    @validator("name")
    def validate_bucket_name(cls, v):
        # S3-like naming conventions
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Invalid bucket name")
        return v.lower()
```

**Benefits:**
- Prevents path traversal attacks
- Input validation at the schema level
- File size limits to prevent DoS
- Proper error messages without leaking system info

### 5. Metadata Handling

**Before:**
- No metadata tracking
- No content type detection
- No file integrity verification

**After:**
```python
class ObjectMetadata(BaseModel):
    key: str
    bucket: str
    size: int
    content_type: str
    etag: str  # MD5 checksum
    last_modified: datetime

# Computed during upload
async def put_object(self, ...):
    md5_hash = hashlib.md5()
    total_size = 0
    
    async with aiofiles.open(object_path, "wb") as f:
        while chunk := await file.read(settings.chunk_size):
            md5_hash.update(chunk)
            total_size += len(chunk)
            await f.write(chunk)
    
    etag = md5_hash.hexdigest()
    # Return complete metadata
```

**Benefits:**
- File integrity verification via ETag
- Content-Type preservation
- S3-compatible metadata structure
- Proper HTTP headers in responses

### 6. Error Handling

**Before:**
```python
if not file_path:
    raise HTTPException(status_code=404, detail="File not found")
```

**After:**
```python
# Custom exception hierarchy
class StorageException(Exception): ...
class BucketNotFoundError(StorageException): ...
class ObjectNotFoundError(StorageException): ...

# Global exception handlers
@app.exception_handler(ObjectNotFoundError)
async def object_not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "ObjectNotFound",
            "detail": str(exc),
            "code": "NoSuchKey"  # S3-compatible error codes
        }
    )
```

**Benefits:**
- Consistent error responses
- S3-compatible error codes
- Separation of concerns (business logic vs HTTP)
- Better debugging information

### 7. Streaming Operations

**Memory-Efficient Uploads:**
```python
# Upload streaming with checksum
async with aiofiles.open(object_path, "wb") as f:
    while chunk := await file.read(settings.chunk_size):
        md5_hash.update(chunk)
        await f.write(chunk)
```

**Memory-Efficient Downloads:**
```python
async def file_stream():
    async with aiofiles.open(object_path, "rb") as f:
        while chunk := await f.read(settings.chunk_size):
            yield chunk

return StreamingResponse(
    file_stream(),
    media_type=metadata.content_type,
    headers={"Content-Length": str(metadata.size)}
)
```

**Benefits:**
- Handles files larger than available RAM
- Constant memory footprint
- Better concurrency (doesn't block on large files)
- Proper streaming HTTP responses

## Performance Characteristics

### Memory Usage
- **Before:** O(file_size) - entire file loaded in memory
- **After:** O(chunk_size) - constant memory usage (default 1MB)

### Concurrency
- **Before:** Blocking I/O
- **After:** Async I/O with aiofiles, multiple requests handled concurrently

### Throughput
- Configurable chunk size for optimal I/O performance
- Streaming responses for immediate data transfer
- Worker process pool for CPU-bound operations

## Testing & Validation

### Unit Testing Support
```python
# Mock storage backend for testing
class MockStorageBackend(StorageBackend):
    def __init__(self):
        self.buckets = {}
        self.objects = {}
    # ... implement methods for testing
```

### Integration Testing
- `test_system.py` - Tests core functionality
- `test_client.py` - Python client example
- `test_api.sh` - Shell script for API testing

## Deployment Options

### 1. Local Development
```bash
uvicorn app.main:app --reload
```

### 2. Docker
```bash
docker-compose up
```

### 3. Production (Systemd)
```bash
systemctl start object-storage
```

### 4. Kubernetes (Future)
- StatefulSet for storage persistence
- Horizontal Pod Autoscaler for scaling
- PersistentVolume for storage backend

## Future Extensibility

### Adding New Storage Backends

```python
class S3Backend(StorageBackend):
    """AWS S3 backend implementation"""
    def __init__(self, aws_access_key, aws_secret_key, region):
        self.s3_client = boto3.client('s3', ...)
    
    async def put_object(self, bucket, key, file):
        # Upload to S3
        await self.s3_client.upload_fileobj(...)

class MinIOBackend(StorageBackend):
    """MinIO backend implementation"""
    # Similar to S3Backend

# In config.py
if settings.storage_backend == "s3":
    storage_backend = S3Backend(...)
elif settings.storage_backend == "minio":
    storage_backend = MinIOBackend(...)
else:
    storage_backend = LocalFilesystemBackend(...)
```

### Adding Authentication

```python
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/{bucket}")
async def upload_object(
    bucket: str,
    file: UploadFile,
    token: str = Depends(oauth2_scheme)
):
    user = verify_token(token)
    # ... upload logic
```

### Adding Object Versioning

```python
class ObjectMetadata(BaseModel):
    # ... existing fields
    version_id: str
    is_latest: bool

# Storage backend modification
async def put_object(self, bucket, key, file):
    version_id = str(uuid.uuid4())
    storage_key = f"{key}/.versions/{version_id}"
    # ... store with version
```

## Comparison with AWS S3

| Feature | Our Implementation | AWS S3 | Status |
|---------|-------------------|--------|--------|
| Buckets | ✅ | ✅ | Implemented |
| Objects | ✅ | ✅ | Implemented |
| Metadata | ✅ | ✅ | Implemented |
| Streaming | ✅ | ✅ | Implemented |
| ETag/MD5 | ✅ | ✅ | Implemented |
| Path Security | ✅ | ✅ | Implemented |
| Versioning | ❌ | ✅ | Future |
| ACLs | ❌ | ✅ | Future |
| Pre-signed URLs | ❌ | ✅ | Future |
| Multi-part upload | ❌ | ✅ | Future |
| Encryption | ❌ | ✅ | Future |
| Lifecycle policies | ❌ | ✅ | Future |

## Conclusion

The refactored system provides:
- **Production-ready** code with proper error handling
- **Scalable** architecture that can grow with requirements
- **Secure** implementation with multiple layers of protection
- **Maintainable** codebase following best practices
- **Extensible** design for future enhancements
- **Well-documented** with comprehensive guides

This creates a solid foundation for a self-hosted object storage service that can compete with commercial solutions while maintaining full control over your data.
