#!/bin/bash
# Test script for Librarian service
# Archive-AI v7.5 - Phase 5.1

set -e

echo "🧪 Testing Librarian Service (Phase 5.1)"
echo "========================================"
echo

# Create test file
TEST_FILE=~/ArchiveAI/Library-Drop/test-document.txt

echo "📝 Creating test document..."
cat > "$TEST_FILE" << 'EOF'
Archive-AI Library Ingestion Test Document

This is a test document for validating the librarian service.
It contains multiple sentences to test the chunking algorithm.

The chunking system should split this into pieces of approximately 250 tokens.
Each chunk will have 50 tokens of overlap to preserve context.

This ensures that no information is lost at chunk boundaries.
The system uses the tiktoken library for token counting.

Archive-AI v7.5 implements a sophisticated document processing pipeline.
It supports PDF files (with OCR), plain text files, and Markdown documents.

The Titans-inspired memory architecture filters based on surprise scores.
Only novel and important information is stored in the vector database.

This document should be chunked into 2-3 pieces depending on token count.
Each chunk will include metadata: filename, chunk_index, total_chunks, etc.

Testing complete. This document demonstrates the core functionality
of the library ingestion system in Archive-AI.
EOF

echo "✅ Test document created at: $TEST_FILE"
echo

# Check if librarian is running
echo "🔍 Checking if librarian service is running..."
if docker ps | grep -q librarian; then
    echo "✅ Librarian service is running"

    # Wait a moment for processing
    echo "⏳ Waiting 3 seconds for file processing..."
    sleep 3

    # Check logs
    echo
    echo "📋 Librarian logs (last 20 lines):"
    echo "-----------------------------------"
    docker logs librarian --tail 20

else
    echo "❌ Librarian service not running"
    echo "Starting librarian service..."
    docker-compose up -d librarian

    echo "⏳ Waiting 5 seconds for service to start..."
    sleep 5

    echo
    echo "📋 Librarian logs:"
    echo "-----------------------------------"
    docker logs librarian
fi

echo
echo "🎉 Test complete!"
echo
echo "Next steps:"
echo "  1. Check logs above for 'Processed test-document.txt' message"
echo "  2. Verify chunks were created (should show 2-3 chunks)"
echo "  3. Check for any errors in processing"
echo
echo "To manually add more files:"
echo "  cp your-file.pdf ~/ArchiveAI/Library-Drop/"
echo "  docker logs librarian -f  # Watch processing"
