"""
Document Processing Module
Handles text extraction, OCR, and chunking for library ingestion.
Archive-AI v7.5 - Phase 5.1
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

import PyPDF2
import pytesseract
from pdf2image import convert_from_path
import tiktoken

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Token counting
ENCODING = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer


class DocumentProcessor:
    """Processes documents for library ingestion"""

    def __init__(self, chunk_size: int = 250, chunk_overlap: int = 50):
        """
        Initialize document processor.

        Args:
            chunk_size: Target size for text chunks (in tokens)
            chunk_overlap: Number of overlapping tokens between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        logger.info(f"DocumentProcessor initialized: chunk_size={chunk_size}, overlap={chunk_overlap}")

    def process_document(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Process a document and return chunks with metadata.

        Args:
            file_path: Path to document file

        Returns:
            List of chunks with metadata

        Example:
            [
                {
                    'text': 'Chunk text here...',
                    'tokens': 245,
                    'chunk_index': 0,
                    'filename': 'document.pdf',
                    'file_type': 'pdf',
                    'timestamp': 1234567890,
                    'total_chunks': 5
                },
                ...
            ]
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Extract text based on file type
            file_type = file_path.suffix.lower()

            if file_type == '.pdf':
                text = self._extract_from_pdf(file_path)
            elif file_type in ['.txt', '.md']:
                text = self._extract_from_text(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            # Chunk the text
            chunks = self._chunk_text(text)

            # Add metadata to each chunk
            timestamp = int(datetime.now().timestamp())
            total_chunks = len(chunks)

            result = []
            for idx, chunk_text in enumerate(chunks):
                chunk_tokens = len(ENCODING.encode(chunk_text))

                result.append({
                    'text': chunk_text,
                    'tokens': chunk_tokens,
                    'chunk_index': idx,
                    'filename': file_path.name,
                    'file_type': file_type.lstrip('.'),
                    'timestamp': timestamp,
                    'total_chunks': total_chunks
                })

            logger.info(f"Processed {file_path.name}: {len(text)} chars → {total_chunks} chunks")
            return result

        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            raise

    def _extract_from_pdf(self, file_path: Path) -> str:
        """
        Extract text from PDF using PyPDF2, fallback to OCR if needed.

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text
        """
        try:
            # Try text extraction first (faster)
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text = ""

                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    text += page_text + "\n"

                # If we got reasonable text, use it
                if len(text.strip()) > 100:  # Arbitrary threshold
                    logger.info(f"PDF text extraction successful: {file_path.name}")
                    return self._clean_text(text)

            # If text extraction failed, use OCR
            logger.warning(f"PDF text extraction yielded little text, trying OCR: {file_path.name}")
            return self._ocr_pdf(file_path)

        except Exception as e:
            logger.error(f"PDF extraction failed, trying OCR: {str(e)}")
            return self._ocr_pdf(file_path)

    def _ocr_pdf(self, file_path: Path) -> str:
        """
        OCR a PDF using Tesseract.

        Args:
            file_path: Path to PDF file

        Returns:
            OCR'd text
        """
        try:
            # Convert PDF to images
            images = convert_from_path(str(file_path), dpi=200)

            text = ""
            for page_num, image in enumerate(images):
                # OCR each page
                page_text = pytesseract.image_to_string(image)
                text += page_text + "\n"

                logger.debug(f"OCR'd page {page_num + 1}/{len(images)}")

            logger.info(f"OCR successful: {file_path.name} ({len(images)} pages)")
            return self._clean_text(text)

        except Exception as e:
            logger.error(f"OCR failed for {file_path.name}: {str(e)}")
            raise

    def _extract_from_text(self, file_path: Path) -> str:
        """
        Extract text from TXT or MD file.

        Args:
            file_path: Path to text file

        Returns:
            File contents
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

            logger.info(f"Text extraction successful: {file_path.name}")
            return self._clean_text(text)

        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                text = f.read()

            logger.warning(f"Used latin-1 encoding for {file_path.name}")
            return self._clean_text(text)

    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text (remove excessive whitespace, etc.).

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines
        text = re.sub(r' +', ' ', text)  # Multiple spaces to single space

        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    def _chunk_text(self, text: str) -> List[str]:
        """
        Chunk text into overlapping pieces.

        Uses a sliding window approach with token-based chunking.

        Args:
            text: Full text to chunk

        Returns:
            List of text chunks
        """
        # Split into sentences (rough approximation)
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = len(ENCODING.encode(sentence))

            # If adding this sentence would exceed chunk size, save current chunk
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                # Save chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)

                # Start new chunk with overlap
                # Keep last few sentences for overlap
                overlap_sentences = []
                overlap_tokens = 0

                for s in reversed(current_chunk):
                    s_tokens = len(ENCODING.encode(s))
                    if overlap_tokens + s_tokens <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_tokens += s_tokens
                    else:
                        break

                current_chunk = overlap_sentences
                current_tokens = overlap_tokens

            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        # Don't forget last chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(chunk_text)

        return chunks


def test_processor():
    """Test the document processor with sample files"""
    processor = DocumentProcessor(chunk_size=250, chunk_overlap=50)

    # Test with a sample text file
    test_text = """
    This is a test document. It contains multiple sentences.
    Each sentence will be processed and chunked appropriately.

    The chunking algorithm uses a sliding window with overlap.
    This ensures that context is preserved across chunk boundaries.

    Token counting is done using the tiktoken library.
    This matches OpenAI's tokenization approach.
    """

    # Create temp file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_text * 10)  # Repeat to create multiple chunks
        temp_path = f.name

    try:
        chunks = processor.process_document(temp_path)

        print(f"\n=== Test Results ===")
        print(f"Total chunks: {len(chunks)}")
        print(f"\nFirst chunk:")
        print(f"  Text: {chunks[0]['text'][:100]}...")
        print(f"  Tokens: {chunks[0]['tokens']}")
        print(f"  Metadata: {chunks[0]['filename']}, chunk {chunks[0]['chunk_index']}/{chunks[0]['total_chunks']}")

        if len(chunks) > 1:
            print(f"\nSecond chunk:")
            print(f"  Text: {chunks[1]['text'][:100]}...")
            print(f"  Tokens: {chunks[1]['tokens']}")

            # Check overlap
            overlap_check = chunks[0]['text'][-50:] in chunks[1]['text']
            print(f"  Overlap detected: {overlap_check}")

    finally:
        os.unlink(temp_path)


if __name__ == "__main__":
    test_processor()
