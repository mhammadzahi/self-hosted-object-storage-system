#!/usr/bin/env python3
"""
Python test client for the Object Storage API.
Demonstrates how to interact with the API programmatically.
"""
import io
import requests
from datetime import datetime


class ObjectStorageClient:
    """Simple client for the Object Storage API."""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"
    
    def health_check(self):
        """Check API health."""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def create_bucket(self, name: str):
        """Create a new bucket."""
        response = requests.post(
            f"{self.api_base}/buckets/",
            json={"name": name}
        )
        response.raise_for_status()
        return response.json()
    
    def list_buckets(self):
        """List all buckets."""
        response = requests.get(f"{self.api_base}/buckets/")
        response.raise_for_status()
        return response.json()
    
    def get_bucket(self, name: str):
        """Get bucket information."""
        response = requests.get(f"{self.api_base}/buckets/{name}")
        response.raise_for_status()
        return response.json()
    
    def delete_bucket(self, name: str):
        """Delete a bucket."""
        response = requests.delete(f"{self.api_base}/buckets/{name}")
        response.raise_for_status()
        return response.status_code == 204
    
    def upload_object(self, bucket: str, key: str, content: bytes, content_type: str = None):
        """Upload an object."""
        files = {"file": (key.split("/")[-1], io.BytesIO(content), content_type or "application/octet-stream")}
        data = {"key": key}
        if content_type:
            data["content_type"] = content_type
        
        response = requests.post(
            f"{self.api_base}/objects/{bucket}",
            files=files,
            data=data
        )
        response.raise_for_status()
        return response.json()
    
    def list_objects(self, bucket: str, prefix: str = None):
        """List objects in a bucket."""
        params = {"prefix": prefix} if prefix else {}
        response = requests.get(f"{self.api_base}/objects/{bucket}", params=params)
        response.raise_for_status()
        return response.json()
    
    def download_object(self, bucket: str, key: str):
        """Download an object."""
        response = requests.get(f"{self.api_base}/objects/{bucket}/{key}")
        response.raise_for_status()
        return response.content
    
    def get_object_metadata(self, bucket: str, key: str):
        """Get object metadata."""
        response = requests.head(f"{self.api_base}/objects/{bucket}/{key}")
        response.raise_for_status()
        return {
            "content_type": response.headers.get("Content-Type"),
            "content_length": response.headers.get("Content-Length"),
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
        }
    
    def delete_object(self, bucket: str, key: str):
        """Delete an object."""
        response = requests.delete(f"{self.api_base}/objects/{bucket}/{key}")
        response.raise_for_status()
        return response.status_code == 204


def main():
    """Run example operations."""
    print("🐍 Python Client - Object Storage API Demo\n")
    
    client = ObjectStorageClient()
    
    # Health check
    print("1. Checking API health...")
    health = client.health_check()
    print(f"   Status: {health['status']}, Version: {health['version']}\n")
    
    # Create bucket
    bucket_name = "python-test-bucket"
    print(f"2. Creating bucket '{bucket_name}'...")
    try:
        bucket = client.create_bucket(bucket_name)
        print(f"   ✅ Created: {bucket['name']}\n")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 409:
            print(f"   ⚠️  Bucket already exists\n")
        else:
            raise
    
    # Upload objects
    print("3. Uploading test objects...")
    objects_to_upload = [
        ("data/file1.txt", b"Content of file 1", "text/plain"),
        ("data/file2.json", b'{"key": "value"}', "application/json"),
        ("images/photo.txt", b"Fake image data", "text/plain"),  # Using .txt for simplicity
    ]
    
    for key, content, content_type in objects_to_upload:
        result = client.upload_object(bucket_name, key, content, content_type)
        print(f"   ✅ Uploaded: {result['key']} ({result['size']} bytes, ETag: {result['etag'][:8]}...)")
    print()
    
    # List all objects
    print("4. Listing all objects...")
    objects = client.list_objects(bucket_name)
    print(f"   Total objects: {objects['total']}")
    for obj in objects['objects']:
        print(f"   - {obj['key']} ({obj['size']} bytes)")
    print()
    
    # List with prefix
    print("5. Listing objects with prefix 'data/'...")
    filtered = client.list_objects(bucket_name, prefix="data/")
    print(f"   Found {filtered['total']} objects:")
    for obj in filtered['objects']:
        print(f"   - {obj['key']}")
    print()
    
    # Get metadata
    print("6. Getting metadata for 'data/file1.txt'...")
    metadata = client.get_object_metadata(bucket_name, "data/file1.txt")
    print(f"   Content-Type: {metadata['content_type']}")
    print(f"   Content-Length: {metadata['content_length']}")
    print(f"   ETag: {metadata['etag']}")
    print()
    
    # Download object
    print("7. Downloading 'data/file2.json'...")
    content = client.download_object(bucket_name, "data/file2.json")
    print(f"   Downloaded: {content.decode('utf-8')}\n")
    
    # Delete objects
    print("8. Cleaning up objects...")
    for key, _, _ in objects_to_upload:
        client.delete_object(bucket_name, key)
        print(f"   ✅ Deleted: {key}")
    print()
    
    # Delete bucket
    print(f"9. Deleting bucket '{bucket_name}'...")
    client.delete_bucket(bucket_name)
    print(f"   ✅ Bucket deleted\n")
    
    print("✅ All operations completed successfully!")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API. Is the server running?")
        print("   Start with: python app/main.py")
    except Exception as e:
        print(f"❌ Error: {e}")
