"""
document_ops.py

Loads saved files into LangChain Document objects.
Supports PDF, DOCX, and TXT files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from fastapi import UploadFile
from langchain.schema import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
)

from multi_doc_chat.logger import GLOBAL_LOGGER as log
from multi_doc_chat.exception.custom_exception import DocumentPortalException


def load_documents(paths: Iterable[Path]) -> List[Document]:
    """
    Load files using the appropriate LangChain document loader.

    Args:
        paths: Paths of files already saved by file_io.py.

    Returns:
        List of LangChain Document objects.
    """
    docs: List[Document] = []

    try:
        for path in paths:
            ext = path.suffix.lower()

            # Select loader based on file type.
            if ext == ".pdf":
                loader = PyPDFLoader(str(path))
            elif ext == ".docx":
                loader = Docx2txtLoader(str(path))
            elif ext == ".txt":
                loader = TextLoader(str(path), encoding="utf-8")
            else:
                log.warning("Unsupported extension skipped", path=str(path))
                continue

            docs.extend(loader.load())

        log.info("Documents loaded", count=len(docs))
        return docs

    except Exception as e:
        log.error("Failed loading documents", error=str(e))
        raise DocumentPortalException("Error loading documents", e) from e


class FastAPIFileAdapter:
    """
    Adapts FastAPI UploadFile to the interface expected by file_io.py.

    Provides:
        .name       -> filename
        .getbuffer() -> file bytes
    """

    def __init__(self, upload_file: UploadFile):
        self._file = upload_file
        self.name = upload_file.filename or "file"

    def getbuffer(self) -> bytes:
        """Reset file pointer and return file content as bytes."""
        self._file.file.seek(0)
        return self._file.file.read()


# =============================================================================
# DOCUMENT OPS - PURPOSE & FLOW
# =============================================================================
#
# Purpose:
# Converts saved files into LangChain Document objects for data ingestion.
#
#   Uploaded Files
#        │
#        ▼
#   file_io.py
#   Save Files
#        │
#        ▼
#   document_ops.py
#   load_documents()
#        │
#   ┌────┼─────┐
#   ▼    ▼     ▼
#  PDF  DOCX   TXT
#   │    │     │
#   └────┼─────┘
#        ▼
# LangChain Documents
#        │
#        ▼
# data_ingestion.py
#        │
#        ▼
# Chunking → Embeddings → FAISS
#
# FastAPIFileAdapter:
# FastAPI UploadFile → .name + .getbuffer() → file_io.py
#
# =============================================================================