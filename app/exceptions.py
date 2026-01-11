"""
Custom exceptions for the object storage system.
"""
from fastapi import HTTPException, status


class StorageException(Exception):
    """Base exception for storage-related errors."""
    pass


class BucketNotFoundError(StorageException):
    """Raised when a bucket does not exist."""
    def __init__(self, bucket: str):
        self.bucket = bucket
        super().__init__(f"Bucket '{bucket}' not found")


class BucketAlreadyExistsError(StorageException):
    """Raised when attempting to create a bucket that already exists."""
    def __init__(self, bucket: str):
        self.bucket = bucket
        super().__init__(f"Bucket '{bucket}' already exists")


class ObjectNotFoundError(StorageException):
    """Raised when an object does not exist."""
    def __init__(self, bucket: str, key: str):
        self.bucket = bucket
        self.key = key
        super().__init__(f"Object '{key}' not found in bucket '{bucket}'")


class InvalidPathError(StorageException):
    """Raised when path traversal or invalid path is detected."""
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Invalid or unsafe path: {path}")


class FileSizeLimitExceededError(StorageException):
    """Raised when file size exceeds the maximum allowed size."""
    def __init__(self, size: int, max_size: int):
        self.size = size
        self.max_size = max_size
        super().__init__(f"File size {size} bytes exceeds maximum allowed size {max_size} bytes")


# HTTP Exception helpers
def bucket_not_found_http(bucket: str) -> HTTPException:
    """Create HTTP 404 exception for bucket not found."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Bucket '{bucket}' not found"
    )


def object_not_found_http(bucket: str, key: str) -> HTTPException:
    """Create HTTP 404 exception for object not found."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Object '{key}' not found in bucket '{bucket}'"
    )


def bucket_already_exists_http(bucket: str) -> HTTPException:
    """Create HTTP 409 exception for bucket already exists."""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Bucket '{bucket}' already exists"
    )


def invalid_path_http(path: str) -> HTTPException:
    """Create HTTP 400 exception for invalid path."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid or unsafe path detected"
    )


def file_too_large_http(size: int, max_size: int) -> HTTPException:
    """Create HTTP 413 exception for file too large."""
    return HTTPException(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        detail=f"File size exceeds maximum allowed size of {max_size} bytes"
    )
