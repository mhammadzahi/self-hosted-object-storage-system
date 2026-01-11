"""
Pydantic schemas for request/response validation and API contracts.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


# Bucket Schemas
class BucketCreate(BaseModel):
    """Request schema for creating a bucket."""
    name: str = Field(..., min_length=3, max_length=63, description="Bucket name (3-63 characters)")
    
    @validator("name")
    def validate_bucket_name(cls, v):
        """Validate bucket name follows S3-like naming conventions."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Bucket name must contain only alphanumeric characters, hyphens, and underscores")
        if v.startswith("-") or v.startswith("_"):
            raise ValueError("Bucket name cannot start with hyphen or underscore")
        return v.lower()


class BucketResponse(BaseModel):
    """Response schema for bucket operations."""
    name: str
    created_at: datetime
    object_count: int = 0
    total_size: int = 0


class BucketList(BaseModel):
    """Response schema for listing buckets."""
    buckets: list[BucketResponse]
    total: int


# Object Schemas
class ObjectMetadata(BaseModel):
    """Object metadata schema."""
    key: str = Field(..., description="Object key/path")
    bucket: str = Field(..., description="Bucket name")
    size: int = Field(..., description="Size in bytes")
    content_type: str = Field(..., description="MIME content type")
    etag: str = Field(..., description="MD5 checksum/ETag")
    last_modified: datetime = Field(..., description="Last modification timestamp")
    storage_path: Optional[str] = Field(None, description="Internal storage path")


class ObjectUploadResponse(BaseModel):
    """Response schema for object upload."""
    key: str
    bucket: str
    size: int
    etag: str
    content_type: str
    uploaded_at: datetime


class ObjectListItem(BaseModel):
    """Item in object listing."""
    key: str
    size: int
    last_modified: datetime
    etag: str
    content_type: str


class ObjectList(BaseModel):
    """Response schema for listing objects."""
    bucket: str
    objects: list[ObjectListItem]
    total: int
    prefix: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    error: str
    detail: str
    code: str


class HealthCheck(BaseModel):
    """Health check response."""
    status: str
    version: str
    storage_backend: str
    timestamp: datetime
