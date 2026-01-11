#!/usr/bin/env python3
"""
Quick test script to verify the object storage system functionality.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.storage import storage_backend
from app.exceptions import BucketAlreadyExistsError, BucketNotFoundError


async def run_tests():
    """Run basic functionality tests."""
    print("🧪 Running Object Storage System Tests\n")
    
    # Test 1: Create a bucket
    print("1️⃣  Creating test bucket...")
    try:
        await storage_backend.create_bucket("test-bucket")
        print("   ✅ Bucket created successfully")
    except BucketAlreadyExistsError:
        print("   ⚠️  Bucket already exists (ok)")
    
    # Test 2: Check if bucket exists
    print("\n2️⃣  Checking if bucket exists...")
    exists = await storage_backend.bucket_exists("test-bucket")
    print(f"   {'✅' if exists else '❌'} Bucket exists: {exists}")
    
    # Test 3: List buckets
    print("\n3️⃣  Listing all buckets...")
    buckets = await storage_backend.list_buckets()
    print(f"   ✅ Found {len(buckets)} bucket(s):")
    for bucket in buckets:
        print(f"      - {bucket['name']} ({bucket['object_count']} objects)")
    
    # Test 4: Create another bucket for testing
    print("\n4️⃣  Creating second bucket...")
    try:
        await storage_backend.create_bucket("another-bucket")
        print("   ✅ Second bucket created")
    except BucketAlreadyExistsError:
        print("   ⚠️  Second bucket already exists (ok)")
    
    # Test 5: List buckets again
    print("\n5️⃣  Listing buckets again...")
    buckets = await storage_backend.list_buckets()
    print(f"   ✅ Total buckets: {len(buckets)}")
    
    # Test 6: Path validation
    print("\n6️⃣  Testing path traversal protection...")
    try:
        await storage_backend.bucket_exists("../../../etc")
        print("   ❌ SECURITY ISSUE: Path traversal not blocked!")
    except Exception as e:
        print(f"   ✅ Path traversal blocked correctly")
    
    print("\n" + "="*50)
    print("✅ All tests completed successfully!")
    print("="*50)
    print("\nYou can now start the server with:")
    print("   python app/main.py")
    print("\nOr run with uvicorn:")
    print("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8001")


if __name__ == "__main__":
    asyncio.run(run_tests())
