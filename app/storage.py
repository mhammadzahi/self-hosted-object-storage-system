"""
Storage abstraction layer with async operations, streaming, and security.
Implements local filesystem backend with extensibility for future backends (S3, MinIO, GCS).
"""
import hashlib
import mimetypes
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Optional

import aiofiles
from fastapi import UploadFile

from app.config import settings
from app.exceptions import (
    BucketAlreadyExistsError,
    BucketNotFoundError,
    InvalidPathError,
    ObjectNotFoundError,
    FileSizeLimitExceededError,
)
from app.schemas import ObjectMetadata


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    async def create_bucket(self, bucket: str) -> None:
        """Create a new bucket."""
        pass
    
    @abstractmethod
    async def delete_bucket(self, bucket: str) -> None:
        """Delete a bucket."""
        pass
    
    @abstractmethod
    async def list_buckets(self) -> list[dict]:
        """List all buckets."""
        pass
    
    @abstractmethod
    async def bucket_exists(self, bucket: str) -> bool:
        """Check if bucket exists."""
        pass
    
    @abstractmethod
    async def put_object(
        self, 
        bucket: str, 
        key: str, 
        file: UploadFile,
        content_type: Optional[str] = None
    ) -> ObjectMetadata:
        """Upload an object."""
        pass
    
    @abstractmethod
    async def get_object(self, bucket: str, key: str) -> tuple[Path, ObjectMetadata]:
        """Get object path and metadata."""
        pass
    
    @abstractmethod
    async def delete_object(self, bucket: str, key: str) -> None:
        """Delete an object."""
        pass
    
    @abstractmethod
    async def list_objects(self, bucket: str, prefix: Optional[str] = None) -> list[ObjectMetadata]:
        """List objects in a bucket."""
        pass
    
    @abstractmethod
    async def get_object_metadata(self, bucket: str, key: str) -> ObjectMetadata:
        """Get object metadata without downloading."""
        pass


class LocalFilesystemBackend(StorageBackend):
    """
    Local filesystem implementation of storage backend.
    - Buckets are top-level directories
    - Objects are files within buckets
    - Metadata stored in file attributes and computed on-demand
    """
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _validate_bucket_name(self, bucket: str) -> str:
        """Validate and sanitize bucket name to prevent path traversal."""
        if not bucket or ".." in bucket or "/" in bucket or "\\" in bucket:
            raise InvalidPathError(bucket)
        # Additional validation: alphanumeric, hyphens, underscores only
        if not bucket.replace("-", "").replace("_", "").isalnum():
            raise InvalidPathError(bucket)
        return bucket.lower()
    
    def _validate_object_key(self, key: str) -> str:
        """Validate and sanitize object key to prevent path traversal."""
        if not key or ".." in key:
            raise InvalidPathError(key)
        # Normalize path separators
        key = key.replace("\\", "/")
        # Remove leading slashes
        key = key.lstrip("/")
        if not key:
            raise InvalidPathError("Empty key after normalization")
        return key
    
    def _get_bucket_path(self, bucket: str) -> Path:
        """Get the filesystem path for a bucket."""
        bucket = self._validate_bucket_name(bucket)
        bucket_path = self.base_path / bucket
        # Ensure the resolved path is within base_path (defense in depth)
        if settings.enable_path_traversal_protection:
            resolved = bucket_path.resolve()
            if not str(resolved).startswith(str(self.base_path.resolve())):
                raise InvalidPathError(bucket)
        return bucket_path
    
    def _get_object_path(self, bucket: str, key: str) -> Path:
        """Get the filesystem path for an object."""
        bucket_path = self._get_bucket_path(bucket)
        key = self._validate_object_key(key)
        object_path = bucket_path / key
        # Ensure the resolved path is within bucket_path
        if settings.enable_path_traversal_protection:
            resolved = object_path.resolve()
            if not str(resolved).startswith(str(bucket_path.resolve())):
                raise InvalidPathError(key)
        return object_path
    
    async def create_bucket(self, bucket: str) -> None:
        """Create a new bucket (directory)."""
        bucket_path = self._get_bucket_path(bucket)
        if bucket_path.exists():
            raise BucketAlreadyExistsError(bucket)
        bucket_path.mkdir(parents=True, exist_ok=False)
    
    async def delete_bucket(self, bucket: str) -> None:
        """Delete a bucket (must be empty)."""
        bucket_path = self._get_bucket_path(bucket)
        if not bucket_path.exists():
            raise BucketNotFoundError(bucket)
        # Check if bucket is empty
        if any(bucket_path.iterdir()):
            raise ValueError(f"Bucket '{bucket}' is not empty")
        bucket_path.rmdir()
    
    async def list_buckets(self) -> list[dict]:
        """List all buckets."""
        buckets = []
        for item in self.base_path.iterdir():
            if item.is_dir():
                # Calculate bucket stats
                object_count = sum(1 for _ in item.rglob("*") if _.is_file())
                total_size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                created_at = datetime.fromtimestamp(item.stat().st_ctime)
                buckets.append({
                    "name": item.name,
                    "created_at": created_at,
                    "object_count": object_count,
                    "total_size": total_size,
                })
        return buckets
    
    async def bucket_exists(self, bucket: str) -> bool:
        """Check if bucket exists. Raises InvalidPathError for invalid paths."""
        bucket_path = self._get_bucket_path(bucket)
        return bucket_path.exists() and bucket_path.is_dir()
    
    async def put_object(
        self, 
        bucket: str, 
        key: str, 
        file: UploadFile,
        content_type: Optional[str] = None
    ) -> ObjectMetadata:
        """
        Upload an object with streaming to avoid loading entire file in memory.
        Computes MD5 checksum during upload.
        """
        if not await self.bucket_exists(bucket):
            raise BucketNotFoundError(bucket)
        
        object_path = self._get_object_path(bucket, key)
        
        # Create parent directories if needed
        object_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Determine content type
        if content_type is None:
            content_type = file.content_type or "application/octet-stream"
            # Try to guess from filename
            if content_type == "application/octet-stream":
                guessed_type, _ = mimetypes.guess_type(key)
                if guessed_type:
                    content_type = guessed_type
        
        # Stream file to disk with checksum calculation
        md5_hash = hashlib.md5()
        total_size = 0
        
        async with aiofiles.open(object_path, "wb") as f:
            while chunk := await file.read(settings.chunk_size):
                # Check file size limit
                total_size += len(chunk)
                if total_size > settings.max_file_size:
                    # Clean up partial file
                    await f.close()
                    object_path.unlink(missing_ok=True)
                    raise FileSizeLimitExceededError(total_size, settings.max_file_size)
                
                md5_hash.update(chunk)
                await f.write(chunk)
        
        etag = md5_hash.hexdigest()
        
        # Store metadata as extended attributes or in a separate metadata file
        # For simplicity, we'll compute it on-demand from filesystem
        
        return ObjectMetadata(
            key=key,
            bucket=bucket,
            size=total_size,
            content_type=content_type,
            etag=etag,
            last_modified=datetime.fromtimestamp(object_path.stat().st_mtime),
            storage_path=str(object_path)
        )
    
    async def get_object(self, bucket: str, key: str) -> tuple[Path, ObjectMetadata]:
        """Get object path and metadata for streaming download."""
        if not await self.bucket_exists(bucket):
            raise BucketNotFoundError(bucket)
        
        object_path = self._get_object_path(bucket, key)
        
        if not object_path.exists() or not object_path.is_file():
            raise ObjectNotFoundError(bucket, key)
        
        metadata = await self.get_object_metadata(bucket, key)
        return object_path, metadata
    
    async def delete_object(self, bucket: str, key: str) -> None:
        """Delete an object."""
        if not await self.bucket_exists(bucket):
            raise BucketNotFoundError(bucket)
        
        object_path = self._get_object_path(bucket, key)
        
        if not object_path.exists():
            raise ObjectNotFoundError(bucket, key)
        
        object_path.unlink()
        
        # Clean up empty parent directories
        try:
            parent = object_path.parent
            while parent != self._get_bucket_path(bucket):
                if not any(parent.iterdir()):
                    parent.rmdir()
                    parent = parent.parent
                else:
                    break
        except OSError:
            pass  # Directory not empty or other issues
    
    async def list_objects(self, bucket: str, prefix: Optional[str] = None) -> list[ObjectMetadata]:
        """List objects in a bucket with optional prefix filter."""
        if not await self.bucket_exists(bucket):
            raise BucketNotFoundError(bucket)
        
        bucket_path = self._get_bucket_path(bucket)
        objects = []
        
        for file_path in bucket_path.rglob("*"):
            if file_path.is_file():
                # Get relative path from bucket
                relative_path = file_path.relative_to(bucket_path)
                key = str(relative_path).replace(os.sep, "/")
                
                # Apply prefix filter
                if prefix and not key.startswith(prefix):
                    continue
                
                # Compute metadata
                stat = file_path.stat()
                content_type, _ = mimetypes.guess_type(str(file_path))
                content_type = content_type or "application/octet-stream"
                
                # Compute ETag (MD5) - for large files, this could be optimized
                md5_hash = hashlib.md5()
                async with aiofiles.open(file_path, "rb") as f:
                    while chunk := await f.read(settings.chunk_size):
                        md5_hash.update(chunk)
                etag = md5_hash.hexdigest()
                
                objects.append(ObjectMetadata(
                    key=key,
                    bucket=bucket,
                    size=stat.st_size,
                    content_type=content_type,
                    etag=etag,
                    last_modified=datetime.fromtimestamp(stat.st_mtime),
                ))
        
        return objects
    
    async def get_object_metadata(self, bucket: str, key: str) -> ObjectMetadata:
        """Get object metadata without downloading the file."""
        if not await self.bucket_exists(bucket):
            raise BucketNotFoundError(bucket)
        
        object_path = self._get_object_path(bucket, key)
        
        if not object_path.exists() or not object_path.is_file():
            raise ObjectNotFoundError(bucket, key)
        
        stat = object_path.stat()
        content_type, _ = mimetypes.guess_type(str(object_path))
        content_type = content_type or "application/octet-stream"
        
        # Compute ETag (MD5 checksum)
        md5_hash = hashlib.md5()
        async with aiofiles.open(object_path, "rb") as f:
            while chunk := await f.read(settings.chunk_size):
                md5_hash.update(chunk)
        etag = md5_hash.hexdigest()
        
        return ObjectMetadata(
            key=key,
            bucket=bucket,
            size=stat.st_size,
            content_type=content_type,
            etag=etag,
            last_modified=datetime.fromtimestamp(stat.st_mtime),
            storage_path=str(object_path)
        )


# Global storage instance
storage_backend: StorageBackend = LocalFilesystemBackend(settings.get_storage_path())

