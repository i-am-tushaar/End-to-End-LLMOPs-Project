
"""
Unit tests for document_ops.py

Purpose:
- Test loading PDF, DOCX, and TXT files.
- Test handling of unsupported file types and loading errors.
- Test the FastAPIFileAdapter class.
"""

from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import UploadFile
from langchain_core.documents import Document

from multi_doc_chat.utils.document_ops import (
    load_documents,
    FastAPIFileAdapter,
)
from multi_doc_chat.exception.custom_exception import DocumentPortalException


# ---------------------------------------------------------
# 1. Test PDF document loading
# ---------------------------------------------------------
@patch("multi_doc_chat.utils.document_ops.PyPDFLoader")
def test_load_pdf_documents(mock_loader):
    # Mock the PDF loader so the test doesn't need a real PDF file.
    # When load() is called, return a sample LangChain Document.
    mock_loader.return_value.load.return_value = [
        Document(page_content="PDF content")
    ]

    # Call the function with a sample PDF path.
    result = load_documents([Path("sample.pdf")])

    # Verify that the document was loaded correctly.
    assert len(result) == 1
    assert result[0].page_content == "PDF content"

    # Verify that the PDF loader received the correct file path.
    mock_loader.assert_called_once_with("sample.pdf")


# ---------------------------------------------------------
# 2. Test DOCX document loading
# ---------------------------------------------------------
@patch("multi_doc_chat.utils.document_ops.Docx2txtLoader")
def test_load_docx_documents(mock_loader):
    # Simulate the DOCX loader returning document content.
    mock_loader.return_value.load.return_value = [
        Document(page_content="DOCX content")
    ]

    # Load a sample DOCX file.
    result = load_documents([Path("sample.docx")])

    # Check that the returned document contains the expected text.
    assert result[0].page_content == "DOCX content"

    # Check that the correct loader was initialized.
    mock_loader.assert_called_once_with("sample.docx")


# ---------------------------------------------------------
# 3. Test TXT document loading
# ---------------------------------------------------------
@patch("multi_doc_chat.utils.document_ops.TextLoader")
def test_load_txt_documents(mock_loader):
    # Simulate the TXT loader returning document content.
    mock_loader.return_value.load.return_value = [
        Document(page_content="TXT content")
    ]

    # Load a sample TXT file.
    result = load_documents([Path("sample.txt")])

    # Verify the returned text.
    assert result[0].page_content == "TXT content"

    # Verify the loader uses UTF-8 encoding.
    mock_loader.assert_called_once_with(
        "sample.txt",
        encoding="utf-8",
    )


# ---------------------------------------------------------
# 4. Test unsupported file extensions
# ---------------------------------------------------------
@patch("multi_doc_chat.utils.document_ops.log")
def test_unsupported_extension_is_skipped(mock_log):
    # XLSX is not a supported extension in document_ops.py.
    # The function should skip it rather than load it.
    result = load_documents([Path("sample.xlsx")])

    # No documents should be returned.
    assert result == []

    # Verify that a warning was logged about the unsupported file.
    mock_log.warning.assert_called_once()


# ---------------------------------------------------------
# 5. Test loading with an empty list of file paths
# ---------------------------------------------------------
def test_load_documents_returns_empty_list():
    # Passing no files should return an empty document list.
    result = load_documents([])

    assert result == []


# ---------------------------------------------------------
# 6. Test handling of a document loader failure
# ---------------------------------------------------------
@patch("multi_doc_chat.utils.document_ops.PyPDFLoader")
def test_loader_error_raises_document_portal_exception(mock_loader):
    # Simulate an error when the PDF loader tries to read a file.
    mock_loader.return_value.load.side_effect = ValueError(
        "Invalid PDF"
    )

    # The original error should be wrapped in the project's
    # custom DocumentPortalException.
    with pytest.raises(DocumentPortalException):
        load_documents([Path("sample.pdf")])


# ---------------------------------------------------------
# 7. Test FastAPIFileAdapter filename and file content
# ---------------------------------------------------------
def test_file_adapter_name_and_getbuffer():
    # Create an in-memory file to avoid creating a real file.
    upload = UploadFile(
        filename="sample.txt",
        file=BytesIO(b"Hello world"),
    )

    # Adapt the FastAPI UploadFile to the interface expected
    # by the project's file-handling code.
    adapter = FastAPIFileAdapter(upload)

    # Verify the adapter exposes the filename and file bytes.
    assert adapter.name == "sample.txt"
    assert adapter.getbuffer() == b"Hello world"


# ---------------------------------------------------------
# 8. Test the default filename when none is provided
# ---------------------------------------------------------
def test_file_adapter_default_name():
    # Simulate an uploaded file without a filename.
    upload = UploadFile(
        filename=None,
        file=BytesIO(b"Test"),
    )

    adapter = FastAPIFileAdapter(upload)

    # The adapter should use "file" as its fallback filename.
    assert adapter.name == "file"


# ---------------------------------------------------------
# 9. Test that getbuffer() resets the file pointer
# ---------------------------------------------------------
def test_file_adapter_resets_file_pointer():
    # Create an in-memory file with known content.
    upload = UploadFile(
        filename="sample.txt",
        file=BytesIO(b"Hello world"),
    )

    # Read the first five bytes, moving the pointer forward.
    upload.file.read(5)

    # Create the adapter and request the file content.
    adapter = FastAPIFileAdapter(upload)

    # getbuffer() should reset the pointer to the beginning
    # so the complete content is returned.
    assert adapter.getbuffer() == b"Hello world"