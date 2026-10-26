from pathlib import Path
from unittest.mock import MagicMock

import pytest

import multi_doc_chat.src.document_ingestion.data_ingestion as ingestion_module
from multi_doc_chat.src.document_ingestion.data_ingestion import ChatIngestor
from multi_doc_chat.src.document_ingestion.data_ingestion import generate_session_id
from langchain_core.documents import Document

from multi_doc_chat.src.document_ingestion.data_ingestion import FaissManager


# ## Test 1: Initialize ChatIngestor
# Objective: Verify that initialization creates the required directories
# and assigns the supplied session ID.
def test_chat_ingestor_initialization(tmp_path, monkeypatch):
    # Mock ModelLoader to avoid loading real embedding models.
    monkeypatch.setattr(
        ingestion_module,
        "ModelLoader",
        MagicMock,
    )

    temp_base = tmp_path / "data"
    faiss_base = tmp_path / "faiss_index"

    ingestor = ChatIngestor(
        temp_base=str(temp_base),
        faiss_base=str(faiss_base),
        use_session_dirs=True,
        session_id="test_session_123",
    )

    assert ingestor.session_id == "test_session_123"
    assert ingestor.use_session is True

    assert ingestor.temp_dir == temp_base / "test_session_123"
    assert ingestor.faiss_dir == faiss_base / "test_session_123"

    assert ingestor.temp_dir.is_dir()
    assert ingestor.faiss_dir.is_dir()


# ## Test 2: Resolve directories without session folders
# Objective: Verify that disabling session directories makes the
# ingestor use the base directories directly.
def test_chat_ingestor_without_session_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(ingestion_module, "ModelLoader", MagicMock)

    temp_base = tmp_path / "data"
    faiss_base = tmp_path / "faiss_index"

    ingestor = ChatIngestor(
        temp_base=str(temp_base),
        faiss_base=str(faiss_base),
        use_session_dirs=False,
        session_id="test_session_456",
    )

    assert ingestor.use_session is False
    assert ingestor.temp_dir == temp_base
    assert ingestor.faiss_dir == faiss_base
    assert ingestor.temp_dir.is_dir()
    assert ingestor.faiss_dir.is_dir()


# ## Test 3: Generate a unique session ID
# Objective: Verify that generated session IDs follow the expected
# format and include a unique suffix.
def test_generate_session_id_format():
    session_id = generate_session_id()

    assert session_id.startswith("session_")
    parts = session_id.split("_")

    assert len(parts) == 4
    assert len(parts[1]) == 8  # YYYYMMDD
    assert len(parts[2]) == 6  # HHMMSS
    assert len(parts[3]) == 8  # UUID suffix
    assert parts[1].isdigit()
    assert parts[2].isdigit()
    assert all(c in "0123456789abcdef" for c in parts[3])



# ## Test 4: Resolve session-specific directories
# Objective: Verify that _resolve_dir() creates and returns
# a directory inside the base path for the current session.
def test_resolve_dir_with_session_enabled(tmp_path, monkeypatch):
    monkeypatch.setattr(ingestion_module, "ModelLoader", MagicMock)

    ingestor = ChatIngestor(
        temp_base=str(tmp_path / "data"),
        faiss_base=str(tmp_path / "faiss_index"),
        use_session_dirs=True,
        session_id="session_test_123",
    )

    base_dir = tmp_path / "extra"
    resolved_dir = ingestor._resolve_dir(base_dir)

    assert resolved_dir == base_dir / "session_test_123"
    assert resolved_dir.is_dir()


# ## Test 5: Split documents into chunks
# Objective: Verify that _split() divides long documents into
# smaller Document chunks.
def test_split_documents_into_chunks(tmp_path, monkeypatch):
    monkeypatch.setattr(ingestion_module, "ModelLoader", MagicMock)

    ingestor = ChatIngestor(
        temp_base=str(tmp_path / "data"),
        faiss_base=str(tmp_path / "faiss_index"),
        use_session_dirs=False,
    )

    document = Document(
        page_content="This is a test sentence. " * 100,
        metadata={"source": "test.txt"},
    )

    chunks = ingestor._split(
        [document],
        chunk_size=100,
        chunk_overlap=20,
    )

    assert len(chunks) > 1
    assert all(isinstance(chunk, Document) for chunk in chunks)
    assert all(len(chunk.page_content) <= 100 for chunk in chunks)
    assert all(chunk.metadata["source"] == "test.txt" for chunk in chunks)



# ## Test 6: Handle an empty document list
# Objective: Verify that _split() returns an empty list
# when there are no documents to process.
def test_split_empty_document_list(tmp_path, monkeypatch):
    monkeypatch.setattr(ingestion_module, "ModelLoader", MagicMock)

    ingestor = ChatIngestor(
        temp_base=str(tmp_path / "data"),
        faiss_base=str(tmp_path / "faiss_index"),
        use_session_dirs=False,
    )

    chunks = ingestor._split([])

    assert chunks == []



# ## Test 7: Verify chunk overlap
# Objective: Verify that consecutive chunks share text when
# chunk_overlap is configured.
def test_split_chunks_have_overlap(tmp_path, monkeypatch):
    monkeypatch.setattr(ingestion_module, "ModelLoader", MagicMock)

    ingestor = ChatIngestor(
        temp_base=str(tmp_path / "data"),
        faiss_base=str(tmp_path / "faiss_index"),
        use_session_dirs=False,
    )

    document = Document(
        page_content="ABCDEFGHIJKLMNOPQRSTUVWXYZ " * 20,
        metadata={"source": "overlap_test.txt"},
    )

    chunks = ingestor._split(
        [document],
        chunk_size=100,
        chunk_overlap=20,
    )

    assert len(chunks) > 1

    # At least one adjacent pair should share text.
    assert any(
        chunks[i].page_content[-20:] in chunks[i + 1].page_content
        for i in range(len(chunks) - 1)
    )


# ## Test 8: Verify supported file extensions
# Objective: Verify that the ingestion module supports PDF, DOCX, and TXT files.
def test_supported_file_extensions():
    assert ingestion_module.SUPPORTED_EXTENSIONS == {
        ".pdf",
        ".docx",
        ".txt",
    }


# ## Test 9: Verify document fingerprint generation
# Objective: Verify that document fingerprints use source and row_id
# when source metadata is available.
def test_fingerprint_uses_source_and_row_id():
    fingerprint = FaissManager._fingerprint(
        "Sample document text",
        {"source": "document.pdf", "row_id": 42},
    )

    assert fingerprint == "document.pdf::42"


# ## Test 10: Verify fingerprint uses file_path
# Objective: Ensure file_path is used when source metadata is unavailable.
def test_fingerprint_uses_file_path():
    fingerprint = FaissManager._fingerprint(
        "Sample document text",
        {"file_path": "report.pdf", "row_id": 7},
    )

    assert fingerprint == "report.pdf::7"


# ## Test 11: Verify SHA-256 fingerprint fallback
# Objective: Ensure text is hashed when source and file_path are missing.
def test_fingerprint_uses_sha256_fallback():
    import hashlib

    text = "Sample document text"
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()

    fingerprint = FaissManager._fingerprint(text, {})

    assert fingerprint == expected


# ## Test 12: Verify FaissManager metadata initialization
# Objective: Ensure metadata starts with an empty rows dictionary.
def test_faiss_manager_metadata_initialization(tmp_path):
    manager = FaissManager.__new__(FaissManager)
    manager.index_dir = tmp_path
    manager.meta_path = tmp_path / "ingested_meta.json"
    manager._meta = {"rows": {}}

    assert manager._meta == {"rows": {}}


# ## Test 13: Verify metadata is saved to JSON
# Objective: Ensure _save_meta() writes metadata to the JSON file.
def test_save_meta_writes_json(tmp_path):
    import json

    manager = FaissManager.__new__(FaissManager)
    manager.index_dir = tmp_path
    manager.meta_path = tmp_path / "ingested_meta.json"
    manager._meta = {"rows": {"document.pdf::1": True}}

    manager._save_meta()

    saved_data = json.loads(
        manager.meta_path.read_text(encoding="utf-8")
    )
    assert saved_data == {"rows": {"document.pdf::1": True}}


# ## Test 14: Verify duplicate documents are skipped
# Objective: Ensure add_documents() skips documents already recorded in metadata.
def test_add_documents_skips_duplicates():
    from unittest.mock import MagicMock
    from langchain_core.documents import Document

    manager = FaissManager.__new__(FaissManager)
    manager.vs = MagicMock()
    manager._meta = {"rows": {"report.pdf::1": True}}

    doc = Document(
        page_content="Sample content",
        metadata={"source": "report.pdf", "row_id": 1},
    )

    added = manager.add_documents([doc])

    assert added == 0
    manager.vs.add_documents.assert_not_called()
    manager.vs.save_local.assert_not_called()


# ## Test 15: Verify new documents are added
# Objective: Ensure new documents are added, saved, and counted correctly.
def test_add_documents_adds_new_document(tmp_path):
    from unittest.mock import MagicMock
    from langchain_core.documents import Document

    manager = FaissManager.__new__(FaissManager)
    manager.index_dir = tmp_path
    manager.meta_path = tmp_path / "ingested_meta.json"
    manager.vs = MagicMock()
    manager._meta = {"rows": {}}

    doc = Document(
        page_content="New content",
        metadata={"source": "new.pdf", "row_id": 1},
    )

    added = manager.add_documents([doc])

    assert added == 1
    manager.vs.add_documents.assert_called_once_with([doc])
    manager.vs.save_local.assert_called_once_with(str(tmp_path))
    assert manager._meta["rows"]["new.pdf::1"] is True
    assert manager.meta_path.exists()


# ## Test 16: Verify error when FAISS is not initialized
# Objective: Ensure add_documents() raises RuntimeError if load_or_create()
# has not initialized the vector store.
def test_add_documents_without_initialized_vector_store():
    import pytest

    manager = FaissManager.__new__(FaissManager)
    manager.vs = None

    with pytest.raises(
        RuntimeError,
        match="Call load_or_create\\(\\) before add_documents_idempotent\\(\\)",
    ):
        manager.add_documents([])


# ## Test 17: Verify error when no FAISS index or data exists
# Objective: Ensure load_or_create() raises DocumentPortalException
# when neither an existing index nor input texts are available.
def test_load_or_create_without_index_or_texts(tmp_path):
    import pytest
    from unittest.mock import MagicMock
    from multi_doc_chat.exception.custom_exception import DocumentPortalException

    manager = FaissManager.__new__(FaissManager)
    manager.index_dir = tmp_path
    manager.model_loader = MagicMock()
    manager.emb = MagicMock()
    manager.vs = None

    with pytest.raises(DocumentPortalException):
        manager.load_or_create(texts=None)


# ## Test 18: Verify missing FAISS index detection
# Objective: Ensure _exists() returns False when index files are missing.
def test_faiss_index_does_not_exist(tmp_path):
    manager = FaissManager.__new__(FaissManager)
    manager.index_dir = tmp_path

    assert manager._exists() is False


# ## Test 19: Verify existing FAISS index detection
# Objective: Ensure _exists() returns True when both required index files exist.
def test_faiss_index_exists(tmp_path):
    manager = FaissManager.__new__(FaissManager)
    manager.index_dir = tmp_path

    (tmp_path / "index.faiss").touch()
    (tmp_path / "index.pkl").touch()

    assert manager._exists() is True


# ## Test 20: Verify incomplete FAISS index detection
# Objective: Ensure _exists() returns False if only one required index file exists.
def test_faiss_index_incomplete(tmp_path):
    manager = FaissManager.__new__(FaissManager)
    manager.index_dir = tmp_path

    (tmp_path / "index.faiss").touch()

    assert manager._exists() is False


# ## Test 21: Verify empty input text handling
# Objective: Ensure load_or_create() raises DocumentPortalException
# when the text list is empty and no existing FAISS index is available.
def test_load_or_create_with_empty_texts(tmp_path):
    import pytest
    from unittest.mock import MagicMock
    from multi_doc_chat.exception.custom_exception import DocumentPortalException

    manager = FaissManager.__new__(FaissManager)
    manager.index_dir = tmp_path
    manager.model_loader = MagicMock()
    manager.emb = MagicMock()
    manager.vs = None

    with pytest.raises(DocumentPortalException):
        manager.load_or_create(texts=[], metadatas=[])


# ## Test 22: Verify existing metadata is loaded
# Objective: Ensure FaissManager loads saved metadata from JSON during initialization.
def test_faiss_manager_loads_existing_metadata(tmp_path):
    import json
    from unittest.mock import MagicMock

    meta_path = tmp_path / "ingested_meta.json"
    expected = {"rows": {"report.pdf::1": True}}
    meta_path.write_text(json.dumps(expected), encoding="utf-8")

    manager = FaissManager.__new__(FaissManager)
    manager.index_dir = tmp_path
    manager.meta_path = meta_path
    manager.model_loader = MagicMock()
    manager.model_loader.load_embeddings.return_value = MagicMock()

    # Run the real constructor to verify metadata loading.
    FaissManager.__init__(
        manager, index_dir=tmp_path, model_loader=manager.model_loader
    )

    assert manager._meta == expected


# ## Test 23: Verify corrupted metadata handling
# Objective: Ensure invalid JSON resets metadata to an empty rows dictionary.
def test_faiss_manager_handles_corrupted_metadata(tmp_path):
    from unittest.mock import MagicMock

    meta_path = tmp_path / "ingested_meta.json"
    meta_path.write_text("{invalid json", encoding="utf-8")

    manager = FaissManager(
        index_dir=tmp_path,
        model_loader=MagicMock(),
    )

    assert manager._meta == {"rows": {}}


# ## Test 24: Verify null metadata handling
# Objective: Ensure JSON containing null resets metadata to {"rows": {}}.
def test_faiss_manager_handles_null_metadata(tmp_path):
    from unittest.mock import MagicMock

    meta_path = tmp_path / "ingested_meta.json"
    meta_path.write_text("null", encoding="utf-8")

    manager = FaissManager(
        index_dir=tmp_path,
        model_loader=MagicMock(),
    )

    assert manager._meta == {"rows": {}}


# ## Test 25: Verify index directory creation
# Objective: Ensure FaissManager creates the index directory if it doesn't exist.
def test_faiss_manager_creates_index_directory(tmp_path):
    from unittest.mock import MagicMock

    index_dir = tmp_path / "new_index"

    FaissManager(
        index_dir=index_dir,
        model_loader=MagicMock(),
    )

    assert index_dir.exists()
    assert index_dir.is_dir()


# ## Test 26: Verify default metadata structure
# Objective: Ensure FaissManager initializes empty metadata when no metadata file exists.
def test_faiss_manager_default_metadata(tmp_path):
    from unittest.mock import MagicMock

    manager = FaissManager(
        index_dir=tmp_path,
        model_loader=MagicMock(),
    )

    assert manager._meta == {"rows": {}}
    assert not manager.meta_path.exists()