# Self-Hosted Object Storage System

A production-ready, self-hosted object storage service built with FastAPI - an AWS S3 alternative with local filesystem backend.

## Features

- **🏗️ Clean Architecture**: Separation of concerns with routers, services, schemas, and configuration layers
- **🔐 Secure by Design**: Path traversal protection, input validation, and sanitization
- **📦 Bucket Management**: S3-like bucket operations (create, list, delete)
- **📁 Object Storage**: Upload, download, list, and delete objects with proper metadata
- **🚀 Streaming Operations**: Memory-efficient streaming for uploads and downloads
- **📊 Metadata Handling**: Content-Type, ETag (MD5), file size, and timestamps
- **⚡ Async Operations**: Fully async/await with aiofiles for non-blocking I/O
- **🔧 Environment Configuration**: Pydantic settings with .env support
- **📝 OpenAPI Documentation**: Auto-generated API docs at `/docs` and `/redoc`
- **🎯 Extensible Design**: Abstract storage backend for future S3/MinIO/GCS support

## Architecture

```
app/
├── __init__.py           # Package initialization
├── main.py               # FastAPI application & middleware
├── config.py             # Environment-based configuration
├── schemas.py            # Pydantic models for validation
├── exceptions.py         # Custom exceptions & error handlers
├── storage.py            # Storage abstraction layer
└── routers/
    ├── __init__.py
    ├── buckets.py        # Bucket management endpoints
    └── objects.py        # Object storage endpoints
```

## Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd self-hosted-object-storage-system
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment** (optional)
```bash
cp .env.example .env
# Edit .env with your settings
```

## Running the Service

### Development
```bash
python app/main.py
```

### Production (with Uvicorn)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
```

### With Gunicorn (recommended for production)
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```

## API Usage

### Health Check
```bash
curl http://localhost:8001/health
```

### Create a Bucket
```bash
curl -X POST http://localhost:8001/api/v1/buckets/ \
  -H "Content-Type: application/json" \
  -d '{"name": "my-bucket"}'
```

### List Buckets
```bash
curl http://localhost:8001/api/v1/buckets/
```

### Upload an Object
```bash
curl -X POST http://localhost:8001/api/v1/objects/my-bucket \
  -F "file=@path/to/file.jpg" \
  -F "key=photos/vacation.jpg"
```

### List Objects in Bucket
```bash
curl http://localhost:8001/api/v1/objects/my-bucket
```

### List Objects with Prefix
```bash
curl "http://localhost:8001/api/v1/objects/my-bucket?prefix=photos/"
```

### Download an Object
```bash
curl http://localhost:8001/api/v1/objects/my-bucket/photos/vacation.jpg \
  --output vacation.jpg
```

### Get Object Metadata (HEAD)
```bash
curl -I http://localhost:8001/api/v1/objects/my-bucket/photos/vacation.jpg
```

### Delete an Object
```bash
curl -X DELETE http://localhost:8001/api/v1/objects/my-bucket/photos/vacation.jpg
```

### Delete a Bucket
```bash
curl -X DELETE http://localhost:8001/api/v1/buckets/my-bucket
```

## Configuration

Environment variables (via `.env` file or system environment):

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | Object Storage API | Application name |
| `APP_VERSION` | 2.0.0 | API version |
| `DEBUG` | false | Debug mode |
| `STORAGE_BACKEND` | local | Storage backend type |
| `STORAGE_BASE_PATH` | UPLOAD_DIR | Base path for storage |
| `MAX_FILE_SIZE` | 5368709120 | Max file size (5GB) |
| `ALLOWED_ORIGINS` | ["*"] | CORS allowed origins |
| `ENABLE_PATH_TRAVERSAL_PROTECTION` | true | Security feature |
| `CHUNK_SIZE` | 1048576 | Streaming chunk size (1MB) |

## Security Features

- **Path Traversal Protection**: Validates and sanitizes all paths
- **Bucket Name Validation**: Enforces S3-like naming conventions
- **File Size Limits**: Configurable maximum file size
- **Input Validation**: Pydantic schemas validate all inputs
- **CORS Configuration**: Configurable allowed origins

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## Design Decisions

### Storage Abstraction Layer
The `StorageBackend` abstract class allows for future implementations:
- MinIO backend
- AWS S3 backend
- Google Cloud Storage backend
- Azure Blob Storage backend

### Streaming Operations
All file operations use streaming to:
- Handle files larger than available RAM
- Reduce memory footprint
- Improve performance with concurrent requests

### Bucket Isolation
- Buckets are top-level directories
- Objects are organized within buckets
- Full path traversal protection prevents escaping bucket boundaries

### Metadata Strategy
- Content-Type: Auto-detected from filename or provided explicitly
- ETag: MD5 checksum computed during upload
- Size: Tracked during streaming upload
- Last Modified: From filesystem metadata

## Future Enhancements

- [ ] Object versioning
- [ ] Multi-part upload support
- [ ] Pre-signed URLs for temporary access
- [ ] Access control lists (ACLs)
- [ ] Bucket policies
- [ ] Cross-origin resource sharing (CORS) per bucket
- [ ] Server-side encryption
- [ ] Object lifecycle management
- [ ] Storage analytics and metrics

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please follow the existing code style and include tests.
