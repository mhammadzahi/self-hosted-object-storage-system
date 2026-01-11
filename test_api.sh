#!/bin/bash
# API Test Script - Comprehensive testing of the Object Storage API
# Usage: ./test_api.sh

set -e  # Exit on error

API_URL="http://localhost:8001"
TEST_BUCKET="test-api-bucket"
TEST_FILE="test-file.txt"

echo "🧪 Object Storage API Test Suite"
echo "=================================="
echo ""

# Create a test file
echo "Hello from Object Storage System!" > /tmp/$TEST_FILE
echo "This is a test upload." >> /tmp/$TEST_FILE

# Test 1: Health Check
echo "1️⃣  Testing health check..."
curl -s "$API_URL/health" | python -m json.tool
echo ""

# Test 2: Create Bucket
echo "2️⃣  Creating bucket '$TEST_BUCKET'..."
curl -s -X POST "$API_URL/api/v1/buckets/" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$TEST_BUCKET\"}" | python -m json.tool
echo ""

# Test 3: List Buckets
echo "3️⃣  Listing all buckets..."
curl -s "$API_URL/api/v1/buckets/" | python -m json.tool
echo ""

# Test 4: Get Bucket Info
echo "4️⃣  Getting bucket info..."
curl -s "$API_URL/api/v1/buckets/$TEST_BUCKET" | python -m json.tool
echo ""

# Test 5: Upload Object
echo "5️⃣  Uploading object..."
curl -s -X POST "$API_URL/api/v1/objects/$TEST_BUCKET" \
  -F "file=@/tmp/$TEST_FILE" \
  -F "key=documents/$TEST_FILE" | python -m json.tool
echo ""

# Test 6: Upload Another Object
echo "6️⃣  Uploading another object..."
echo "Second test file" > /tmp/test-file-2.txt
curl -s -X POST "$API_URL/api/v1/objects/$TEST_BUCKET" \
  -F "file=@/tmp/test-file-2.txt" \
  -F "key=documents/test-file-2.txt" | python -m json.tool
echo ""

# Test 7: List Objects
echo "7️⃣  Listing all objects in bucket..."
curl -s "$API_URL/api/v1/objects/$TEST_BUCKET" | python -m json.tool
echo ""

# Test 8: List Objects with Prefix
echo "8️⃣  Listing objects with prefix 'documents/'..."
curl -s "$API_URL/api/v1/objects/$TEST_BUCKET?prefix=documents/" | python -m json.tool
echo ""

# Test 9: Get Object Metadata (HEAD)
echo "9️⃣  Getting object metadata..."
curl -s -I "$API_URL/api/v1/objects/$TEST_BUCKET/documents/$TEST_FILE"
echo ""

# Test 10: Download Object
echo "🔟 Downloading object..."
curl -s "$API_URL/api/v1/objects/$TEST_BUCKET/documents/$TEST_FILE" -o /tmp/downloaded-$TEST_FILE
echo "Downloaded content:"
cat /tmp/downloaded-$TEST_FILE
echo ""

# Test 11: Delete Object
echo "1️⃣1️⃣  Deleting object..."
curl -s -X DELETE "$API_URL/api/v1/objects/$TEST_BUCKET/documents/$TEST_FILE"
echo "Object deleted"
echo ""

# Test 12: List Objects After Delete
echo "1️⃣2️⃣  Listing objects after deletion..."
curl -s "$API_URL/api/v1/objects/$TEST_BUCKET" | python -m json.tool
echo ""

# Test 13: Delete Remaining Object
echo "1️⃣3️⃣  Deleting remaining object..."
curl -s -X DELETE "$API_URL/api/v1/objects/$TEST_BUCKET/documents/test-file-2.txt"
echo "Object deleted"
echo ""

# Test 14: Delete Bucket
echo "1️⃣4️⃣  Deleting empty bucket..."
curl -s -X DELETE "$API_URL/api/v1/buckets/$TEST_BUCKET"
echo "Bucket deleted"
echo ""

# Test 15: List Buckets After Cleanup
echo "1️⃣5️⃣  Final bucket list..."
curl -s "$API_URL/api/v1/buckets/" | python -m json.tool
echo ""

# Cleanup
rm -f /tmp/$TEST_FILE /tmp/test-file-2.txt /tmp/downloaded-$TEST_FILE

echo "✅ All API tests completed successfully!"
