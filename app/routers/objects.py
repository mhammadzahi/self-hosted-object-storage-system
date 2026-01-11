"""
Object storage API routes.
"""
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, status, Query
from fastapi.responses import StreamingResponse

from app.exceptions import (
    BucketNotFoundError,
    ObjectNotFoundError,
    FileSizeLimitExceededError,
    bucket_not_found_http,
    object_not_found_http,
    file_too_large_http,
)
from app.schemas import ObjectList, ObjectListItem, ObjectMetadata, ObjectUploadResponse
from app.storage import storage_backend
from app.config import settings
import aiofiles


router = APIRouter(prefix="/objects", tags=["Objects"])


@router.post(
    "/{bucket_name}",
    response_model=ObjectUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an object",
    description="Upload a file to the specified bucket. The file is streamed to avoid memory issues."
)
async def upload_object(
    bucket_name: str,
    file: UploadFile = File(..., description="File to upload"),
    key: Optional[str] = Form(None, description="Object key/path. If not provided, uses filename"),
    content_type: Optional[str] = Form(None, description="Content-Type override")
):
    """
    Upload an object to a bucket.
    Supports streaming upload to handle large files efficiently.
    """
    try:
        # Use filename as key if not provided
        object_key = key if key else file.filename
        if not object_key:
            return {"error": "Either 'key' or filename must be provided"}
        
        metadata = await storage_backend.put_object(
            bucket=bucket_name,
            key=object_key,
            file=file,
            content_type=content_type
        )
        
        return ObjectUploadResponse(
            key=metadata.key,
            bucket=metadata.bucket,
            size=metadata.size,
            etag=metadata.etag,
            content_type=metadata.content_type,
            uploaded_at=metadata.last_modified
        )
    
    except BucketNotFoundError as e:
        raise bucket_not_found_http(e.bucket)
    except FileSizeLimitExceededError as e:
        raise file_too_large_http(e.size, e.max_size)


@router.get(
    "/{bucket_name}",
    response_model=ObjectList,
    summary="List objects in bucket",
    description="List all objects in a bucket with optional prefix filtering."
)
async def list_objects(
    bucket_name: str,
    prefix: Optional[str] = Query(None, description="Filter objects by key prefix")
):
    """List objects in a bucket."""
    try:
        objects = await storage_backend.list_objects(bucket_name, prefix=prefix)
        return ObjectList(
            bucket=bucket_name,
            objects=[
                ObjectListItem(
                    key=obj.key,
                    size=obj.size,
                    last_modified=obj.last_modified,
                    etag=obj.etag,
                    content_type=obj.content_type
                )
                for obj in objects
            ],
            total=len(objects),
            prefix=prefix
        )
    except BucketNotFoundError as e:
        raise bucket_not_found_http(e.bucket)


@router.get(
    "/{bucket_name}/{key:path}",
    summary="Download an object",
    description="Download an object from the bucket. Returns the file with streaming support.",
    responses={
        200: {
            "description": "File content",
            "content": {"application/octet-stream": {}},
        }
    }
)
async def download_object(bucket_name: str, key: str):
    """
    Download an object from a bucket.
    Uses streaming response to handle large files efficiently.
    """
    try:
        object_path, metadata = await storage_backend.get_object(bucket_name, key)
        
        # Stream the file
        async def file_stream():
            async with aiofiles.open(object_path, "rb") as f:
                while chunk := await f.read(settings.chunk_size):
                    yield chunk
        
        # Get filename from key (last part of path)
        filename = key.split("/")[-1]
        
        return StreamingResponse(
            file_stream(),
            media_type=metadata.content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(metadata.size),
                "ETag": metadata.etag,
                "Last-Modified": metadata.last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT"),
            }
        )
    
    except BucketNotFoundError as e:
        raise bucket_not_found_http(e.bucket)
    except ObjectNotFoundError as e:
        raise object_not_found_http(e.bucket, e.key)


@router.head(
    "/{bucket_name}/{key:path}",
    summary="Get object metadata",
    description="Retrieve object metadata without downloading the file.",
    status_code=status.HTTP_200_OK
)
async def head_object(bucket_name: str, key: str):
    """Get object metadata (HEAD request)."""
    try:
        metadata = await storage_backend.get_object_metadata(bucket_name, key)
        return {
            "Content-Type": metadata.content_type,
            "Content-Length": str(metadata.size),
            "ETag": metadata.etag,
            "Last-Modified": metadata.last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        }
    except BucketNotFoundError as e:
        raise bucket_not_found_http(e.bucket)
    except ObjectNotFoundError as e:
        raise object_not_found_http(e.bucket, e.key)


@router.delete(
    "/{bucket_name}/{key:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an object",
    description="Delete an object from the bucket."
)
async def delete_object(bucket_name: str, key: str):
    """Delete an object from a bucket."""
    try:
        await storage_backend.delete_object(bucket_name, key)
        return None
    except BucketNotFoundError as e:
        raise bucket_not_found_http(e.bucket)
    except ObjectNotFoundError as e:
        raise object_not_found_http(e.bucket, e.key)
