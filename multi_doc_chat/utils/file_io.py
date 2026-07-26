from __future__ import annotations
import re
import uuid
from pathlib import Path
from typing import Iterable, List
from multi_doc_chat.logger.cutom_logger import CustomLogger
from multi_doc_chat.exception.custom_exception import DocumentPortalException

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".pptx", ".md", ".csv", ".xlsx", ".xls", ".db", ".sqlite", ".sqlite3"}

log = CustomLogger().get_logger(__name__)


def _get_filename(uploaded_file) -> str:
    """Get the original file name from a Starlette UploadFile (.filename) or a generic file-like object (.name)."""
    return getattr(uploaded_file, "filename", getattr(uploaded_file, "name", "file"))


def _read_bytes(uploaded_file) -> bytes:
    """
    Read the raw bytes out of an uploaded file object, whatever shape it comes in as:
      - Starlette UploadFile, which stores the actual file on .file
      - a plain file-like object with .read()
      - anything exposing .getbuffer(), e.g. io.BytesIO
    """
    if hasattr(uploaded_file, "file") and hasattr(uploaded_file.file, "read"):
        data = uploaded_file.file.read()
    elif hasattr(uploaded_file, "read"):
        data = uploaded_file.read()
    elif callable(getattr(uploaded_file, "getbuffer", None)):
        data = uploaded_file.getbuffer()
    else:
        raise ValueError("Unsupported uploaded file object; no readable interface")

    # A memoryview (e.g. from getbuffer()) needs converting before it can be written
    return data.tobytes() if isinstance(data, memoryview) else data


def _safe_filename(original_name: str, ext: str) -> str:
    """Build a unique, filesystem safe file name, keeping a readable trace of the original name."""
    stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", Path(original_name).stem).lower()
    return f"{stem}_{uuid.uuid4().hex[:6]}{ext}"


def save_uploaded_files(uploaded_files: Iterable, target_dir: Path) -> List[Path]:
    """Save uploaded files (Streamlit or Starlette style) to target_dir, and return their local paths."""
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        saved: List[Path] = []

        for uploaded_file in uploaded_files:
            name = _get_filename(uploaded_file)
            ext = Path(name).suffix.lower()

            if ext not in SUPPORTED_EXTENSIONS:
                log.warning("Unsupported file skipped", filename=name)
                continue

            out_path = target_dir / _safe_filename(name, ext)
            out_path.write_bytes(_read_bytes(uploaded_file))

            saved.append(out_path)
            log.info("File saved for ingestion", uploaded=name, saved_as=str(out_path))

        return saved

    except Exception as e:
        log.error("Failed to save uploaded files", error=str(e), dir=str(target_dir))
        raise DocumentPortalException("Failed to save uploaded files", e) from e



# =============================================================================
# FILE I/O - PURPOSE & FLOW
# =============================================================================
#
# Purpose:
# Handles uploaded files before document ingestion.
# It validates file types, creates safe unique filenames,
# reads file content, saves files locally, and returns their paths.
#
# Flow:
#
#   Uploaded Files
#        │
#        ▼
#   _get_filename()
#        │
#        ▼
#   Check Extension ── Unsupported ──► Skip + Log
#        │
#     Supported
#        ▼
#   _safe_filename()
#        │
#        ▼
#   _read_bytes()
#        │
#        ▼
#   Save to target_dir
#        │
#        ▼
#   Return List[Path]
#        │
#        ▼
#   Document Ingestion Pipeline
#
# Supported:
# PDF, DOCX, TXT, PPTX, MD, CSV, Excel, SQLite/DB
#
# =============================================================================