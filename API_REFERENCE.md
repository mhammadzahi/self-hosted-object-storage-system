# Quick Reference - API Endpoints

## Base URL
```
http://localhost:8001
```

## Health & Info

### Health Check
```bash
GET /health
GET /
```

## Bucket Operations

### Create Bucket
```bash
POST /api/v1/buckets/
Content-Type: application/json

{
  "name": "my-bucket"
}
```

### List All Buckets
```bash
GET /api/v1/buckets/
```

### Get Bucket Info
```bash
GET /api/v1/buckets/{bucket_name}
```

### Delete Bucket
```bash
DELETE /api/v1/buckets/{bucket_name}
```
*Note: Bucket must be empty*

## Object Operations

### Upload Object
```bash
POST /api/v1/objects/{bucket_name}
Content-Type: multipart/form-data

file: <binary file data>
key: "path/to/object.txt"  (optional, uses filename if not provided)
content_type: "text/plain"  (optional, auto-detected if not provided)
```

### List Objects in Bucket
```bash
GET /api/v1/objects/{bucket_name}
GET /api/v1/objects/{bucket_name}?prefix=folder/
```

### Download Object
```bash
GET /api/v1/objects/{bucket_name}/{key}
```

### Get Object Metadata
```bash
HEAD /api/v1/objects/{bucket_name}/{key}
```

### Delete Object
```bash
DELETE /api/v1/objects/{bucket_name}/{key}
```

## curl Examples

### Create and Use Bucket
```bash
# Create bucket
curl -X POST http://localhost:8001/api/v1/buckets/ \
  -H "Content-Type: application/json" \
  -d '{"name": "test-bucket"}'

# Upload file
curl -X POST http://localhost:8001/api/v1/objects/test-bucket \
  -F "file=@myfile.txt" \
  -F "key=documents/myfile.txt"

# List objects
curl http://localhost:8001/api/v1/objects/test-bucket

# Download object
curl http://localhost:8001/api/v1/objects/test-bucket/documents/myfile.txt \
  -o downloaded.txt

# Get metadata
curl -I http://localhost:8001/api/v1/objects/test-bucket/documents/myfile.txt

# Delete object
curl -X DELETE http://localhost:8001/api/v1/objects/test-bucket/documents/myfile.txt

# Delete bucket
curl -X DELETE http://localhost:8001/api/v1/buckets/test-bucket
```

## Python Client Example
```python
import requests

# Create bucket
requests.post('http://localhost:8001/api/v1/buckets/', 
              json={'name': 'my-bucket'})

# Upload file
with open('file.txt', 'rb') as f:
    files = {'file': f}
    data = {'key': 'documents/file.txt'}
    requests.post('http://localhost:8001/api/v1/objects/my-bucket',
                  files=files, data=data)

# Download file
response = requests.get('http://localhost:8001/api/v1/objects/my-bucket/documents/file.txt')
with open('downloaded.txt', 'wb') as f:
    f.write(response.content)
```

## Response Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Successful GET/HEAD request |
| 201 | Created | Resource created successfully |
| 204 | No Content | Successful DELETE request |
| 400 | Bad Request | Invalid input or path |
| 404 | Not Found | Bucket or object doesn't exist |
| 409 | Conflict | Bucket already exists |
| 413 | Payload Too Large | File exceeds size limit |
| 500 | Internal Server Error | Server error |

## Error Response Format
```json
{
  "error": "ObjectNotFound",
  "detail": "Object 'file.txt' not found in bucket 'my-bucket'",
  "code": "NoSuchKey"
}
```

## Interactive API Docs

Once the server is running, visit:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc
