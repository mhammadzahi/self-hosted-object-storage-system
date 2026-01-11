"""
Bucket management API routes.
"""
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.exceptions import (
    BucketAlreadyExistsError,
    BucketNotFoundError,
    bucket_already_exists_http,
    bucket_not_found_http,
)
from app.schemas import BucketCreate, BucketList, BucketResponse
from app.storage import storage_backend

router = APIRouter(prefix="/buckets", tags=["Buckets"])


@router.post(
    "/",
    response_model=BucketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new bucket",
    description="Creates a new storage bucket. Bucket names must be unique and follow naming conventions."
)
async def create_bucket(bucket: BucketCreate):
    """Create a new storage bucket."""
    try:
        await storage_backend.create_bucket(bucket.name)
        # Get bucket info
        buckets = await storage_backend.list_buckets()
        bucket_info = next((b for b in buckets if b["name"] == bucket.name), None)
        if bucket_info:
            return BucketResponse(**bucket_info)
        # Fallback if not found in list
        return BucketResponse(
            name=bucket.name,
            created_at=bucket_info["created_at"] if bucket_info else None,
            object_count=0,
            total_size=0
        )
    except BucketAlreadyExistsError as e:
        raise bucket_already_exists_http(e.bucket)


@router.get(
    "/",
    response_model=BucketList,
    summary="List all buckets",
    description="Returns a list of all storage buckets with their metadata."
)
async def list_buckets():
    """List all storage buckets."""
    buckets = await storage_backend.list_buckets()
    return BucketList(
        buckets=[BucketResponse(**b) for b in buckets],
        total=len(buckets)
    )


@router.get(
    "/{bucket_name}",
    response_model=BucketResponse,
    summary="Get bucket information",
    description="Retrieve metadata and statistics for a specific bucket."
)
async def get_bucket(bucket_name: str):
    """Get information about a specific bucket."""
    if not await storage_backend.bucket_exists(bucket_name):
        raise bucket_not_found_http(bucket_name)
    
    buckets = await storage_backend.list_buckets()
    bucket_info = next((b for b in buckets if b["name"] == bucket_name), None)
    
    if not bucket_info:
        raise bucket_not_found_http(bucket_name)
    
    return BucketResponse(**bucket_info)


@router.delete(
    "/{bucket_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a bucket",
    description="Delete an empty bucket. Bucket must not contain any objects."
)
async def delete_bucket(bucket_name: str):
    """Delete a bucket (must be empty)."""
    try:
        await storage_backend.delete_bucket(bucket_name)
        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content=None
        )
    except BucketNotFoundError as e:
        raise bucket_not_found_http(e.bucket)
    except ValueError as e:
        # Bucket not empty
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(e)}
        )
