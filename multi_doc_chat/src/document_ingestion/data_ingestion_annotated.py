"""
data_ingestion.py

Handles the document ingestion pipeline for the multi-document RAG system.

Responsibilities:
    1. Save uploaded files using file_io.py.
    2. Load saved files using document_ops.py.
    3. Split documents into smaller chunks.
    4. Load the embedding model using model_loader.py.
    5. Create or load a FAISS vector store.
    6. Add only new document chunks to FAISS.
    7. Return a configured retriever for the RAG pipeline.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from multi_doc_chat.exception.custom_exception import DocumentPortalException
from multi_doc_chat.logger import GLOBAL_LOGGER as log
from multi_doc_chat.utils.document_ops import load_documents
from multi_doc_chat.utils.file_io import save_uploaded_files
from multi_doc_chat.utils.model_loader import ModelLoader


# =============================================================================
# SESSION
# =============================================================================

def generate_session_id() -> str:
    """
    Generate a unique session ID.

    Example:
        session_20260726_153045_a1b2c3d4
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]

    return f"session_{timestamp}_{unique_id}"


# =============================================================================
# CHAT INGESTOR
# =============================================================================

class ChatIngestor:
    """
    Coordinates the complete document ingestion pipeline.

    Flow:
        Upload files
            -> Save files
            -> Load documents
            -> Split into chunks
            -> Create/load FAISS
            -> Add new chunks
            -> Return retriever
    """

    def __init__(self, temp_base: str = "data", faiss_base: str = "faiss_index", 
        use_session_dirs: bool = True, session_id: Optional[str] = None,):
        """
        Initialize the ingestion pipeline.

        Args:
            temp_base:
                Base directory where uploaded files are stored.

            faiss_base:
                Base directory where FAISS indexes are stored.

            use_session_dirs:
                If True, create separate directories for each session.

            session_id:
                Optional custom session ID. If not provided, one is generated.
        """
        try:
            # Centralized model/embedding loader
            self.model_loader = ModelLoader()

            self.use_session = use_session_dirs
            self.session_id = session_id or generate_session_id()

            # Resolve and create directories
            self.temp_dir = self._resolve_dir(Path(temp_base))
            self.faiss_dir = self._resolve_dir(Path(faiss_base))

            log.info(
                "ChatIngestor initialized",
                session_id=self.session_id,
                temp_dir=str(self.temp_dir),
                faiss_dir=str(self.faiss_dir),
                sessionized=self.use_session,
            )

        except Exception as e:
            log.error("Failed to initialize ChatIngestor", error=str(e))
            raise DocumentPortalException( "Initialization error in ChatIngestor", e) from e

    def _resolve_dir(self, base: Path) -> Path:
        """
        Create and return the directory used by the current session.

        Example:

            use_session_dirs=True

            data/
                session_20260726_153045_a1b2c3d4/

        If session directories are disabled:

            data/
        """
        target = base / self.session_id if self.use_session else base

        target.mkdir(parents=True, exist_ok=True)

        return target

    def _split(
        self,
        docs: List[Document],
        chunk_size: int,
        chunk_overlap: int,
    ) -> List[Document]:
        """
        Split documents into smaller overlapping chunks.

        Chunking improves retrieval because the embedding model works with
        smaller, focused pieces of text instead of entire documents.
        """
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size,chunk_overlap=chunk_overlap)
        chunks = splitter.split_documents(docs)

        log.info("Documents split",documents=len(docs),chunks=len(chunks),chunk_size=chunk_size,
            overlap=chunk_overlap)

        return chunks

    def build_retriever(
        self,
        uploaded_files: Iterable,
        *,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        k: int = 5,
        search_type: str = "mmr",
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
    ):
        """
        Run the complete ingestion pipeline and return a FAISS retriever.

        Args:
            uploaded_files:
                Uploaded files from FastAPI, Streamlit, or another interface.

            chunk_size:
                Maximum size of each document chunk.

            chunk_overlap:
                Number of characters shared between neighboring chunks.

            k:
                Number of documents returned by the retriever.

            search_type:
                FAISS retrieval strategy.
                Common options:
                    - "similarity"
                    - "mmr"

            fetch_k:
                For MMR, number of candidate documents retrieved before
                diversity re-ranking.

            lambda_mult:
                MMR relevance/diversity balance.

                0.0 -> maximum diversity
                1.0 -> maximum relevance

        Returns:
            Configured LangChain FAISS retriever.
        """
        try:
            # -------------------------------------------------------------
            # 1. Save uploaded files
            # -------------------------------------------------------------
            # File validation, safe filenames, and byte writing are handled
            # centrally by file_io.py.
            paths = save_uploaded_files(
                uploaded_files,
                self.temp_dir,
            )

            if not paths:
                raise ValueError("No supported files were uploaded")

            # -------------------------------------------------------------
            # 2. Load documents
            # -------------------------------------------------------------
            docs = load_documents(paths)

            if not docs:
                raise ValueError("No valid documents could be loaded")

            # -------------------------------------------------------------
            # 3. Split documents into chunks
            # -------------------------------------------------------------
            chunks = self._split(
                docs,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            if not chunks:
                raise ValueError("No document chunks were created")

            # -------------------------------------------------------------
            # 4. Create/load FAISS manager
            # -------------------------------------------------------------
            faiss_manager = FaissManager(
                index_dir=self.faiss_dir,
                model_loader=self.model_loader,
            )

            # Load an existing FAISS index, or initialize a new empty index.
            faiss_manager.load_or_create()

            # -------------------------------------------------------------
            # 5. Add only new chunks
            # -------------------------------------------------------------
            added = faiss_manager.add_documents(chunks)

            log.info(
                "FAISS index updated",
                added=added,
                index=str(self.faiss_dir),
            )

            # -------------------------------------------------------------
            # 6. Configure retriever
            # -------------------------------------------------------------
            search_kwargs: Dict[str, Any] = {
                "k": k,
            }

            if search_type == "mmr":
                search_kwargs["fetch_k"] = fetch_k
                search_kwargs["lambda_mult"] = lambda_mult

                log.info(
                    "Using MMR search",
                    k=k,
                    fetch_k=fetch_k,
                    lambda_mult=lambda_mult,
                )

            # -------------------------------------------------------------
            # 7. Return retriever
            # -------------------------------------------------------------
            if faiss_manager.vs is None:
                raise RuntimeError("FAISS vector store was not initialized")

            return faiss_manager.vs.as_retriever(
                search_type=search_type,
                search_kwargs=search_kwargs,
            )

        except Exception as e:
            log.error(
                "Failed to build retriever",
                error=str(e),
            )

            raise DocumentPortalException(
                "Failed to build retriever",
                e,
            ) from e


# =============================================================================
# FAISS MANAGER
# =============================================================================

class FaissManager:
    """
    Manages the FAISS vector store.

    Responsibilities:
        - Load the embedding model through ModelLoader.
        - Load an existing FAISS index.
        - Create a new FAISS index when needed.
        - Prevent duplicate chunks from being indexed.
        - Save the FAISS index and ingestion metadata.
    """

    def __init__(
        self,
        index_dir: Path,
        model_loader: Optional[ModelLoader] = None,
    ):
        """
        Initialize the FAISS manager.

        Args:
            index_dir:
                Directory where the FAISS index is stored.

            model_loader:
                Optional existing ModelLoader instance. Reusing it avoids
                creating another model loader unnecessarily.
        """
        self.index_dir = Path(index_dir)

        self.index_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Stores fingerprints of chunks that have already been indexed.
        self.meta_path = self.index_dir / "ingested_meta.json"

        self._meta: Dict[str, Any] = self._load_meta()

        # Reuse ModelLoader from ChatIngestor when available.
        self.model_loader = model_loader or ModelLoader()

        # Embedding configuration stays centralized in model_loader.py.
        self.emb = self.model_loader.load_embeddings()

        self.vs: Optional[FAISS] = None

    def _load_meta(self) -> Dict[str, Any]:
        """
        Load metadata containing fingerprints of previously indexed chunks.

        If the metadata file does not exist or cannot be read,
        start with an empty record.
        """
        if self.meta_path.exists():
            try:
                data = json.loads(
                    self.meta_path.read_text(encoding="utf-8")
                )

                if isinstance(data, dict):
                    data.setdefault("rows", {})
                    return data

            except Exception as e:
                log.warning(
                    "Failed to load ingestion metadata",
                    error=str(e),
                    path=str(self.meta_path),
                )

        return {"rows": {}}

    def _save_meta(self) -> None:
        """Save indexed chunk fingerprints to disk."""
        self.meta_path.write_text(
            json.dumps(
                self._meta,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _exists(self) -> bool:
        """Return True when a saved FAISS index exists."""
        return (
            (self.index_dir / "index.faiss").exists()
            and
            (self.index_dir / "index.pkl").exists()
        )

    @staticmethod
    def _fingerprint(
        text: str,
        metadata: Dict[str, Any],
    ) -> str:
        """
        Generate a stable fingerprint for a document chunk.

        The fingerprint is used to detect chunks that have already been
        inserted into FAISS.

        A hash of source + row/page information + text is used so multiple
        chunks from the same source are not incorrectly treated as duplicates.
        """
        source = str(
            metadata.get("source")
            or metadata.get("file_path")
            or ""
        )

        page = str(metadata.get("page", ""))
        row_id = str(metadata.get("row_id", ""))

        fingerprint_input = (
            f"{source}|{page}|{row_id}|{text}"
        )

        return hashlib.sha256(
            fingerprint_input.encode("utf-8")
        ).hexdigest()

    def _is_new(self, doc: Document) -> bool:
        """
        Check whether a document chunk has already been indexed.

        Returns:
            True  -> new chunk
            False -> duplicate chunk
        """
        key = self._fingerprint(
            doc.page_content,
            doc.metadata or {},
        )

        return key not in self._meta["rows"]

    def _mark_indexed(self, docs: List[Document]) -> None:
        """Record document fingerprints after successful FAISS insertion."""
        for doc in docs:
            key = self._fingerprint(
                doc.page_content,
                doc.metadata or {},
            )

            self._meta["rows"][key] = True

    def load_or_create(self) -> FAISS:
        """
        Load an existing FAISS index or initialize a new empty index.

        A new index is created empty here. Documents are added separately
        through add_documents(), which avoids inserting the same chunks twice.
        """
        if self._exists():
            self.vs = FAISS.load_local(
                str(self.index_dir),
                embeddings=self.emb,
                allow_dangerous_deserialization=True,
            )

            log.info(
                "Existing FAISS index loaded",
                index=str(self.index_dir),
            )

            return self.vs

        # FAISS requires at least one vector to initialize, so for a brand-new
        # index we leave self.vs as None. add_documents() will create it from
        # the first batch of new documents.
        log.info(
            "No existing FAISS index found; a new index will be created",
            index=str(self.index_dir),
        )

        return None  # type: ignore

    def add_documents(
        self,
        docs: List[Document],
    ) -> int:
        """
        Add only new chunks to the FAISS index.

        On the first run:
            FAISS.from_documents() creates the index.

        On later runs:
            FAISS.add_documents() adds only unseen chunks.

        Returns:
            Number of newly indexed chunks.
        """
        new_docs = [
            doc
            for doc in docs
            if self._is_new(doc)
        ]

        if not new_docs:
            log.info("No new document chunks to index")
            return 0

        # -------------------------------------------------------------
        # First run: create FAISS from the new documents.
        # -------------------------------------------------------------
        if self.vs is None:
            self.vs = FAISS.from_documents(
                documents=new_docs,
                embedding=self.emb,
            )

        # -------------------------------------------------------------
        # Existing index: append only new documents.
        # -------------------------------------------------------------
        else:
            self.vs.add_documents(new_docs)

        # Save the updated FAISS index.
        self.vs.save_local(
            str(self.index_dir)
        )

        # Only mark chunks as indexed after FAISS insertion succeeds.
        self._mark_indexed(new_docs)
        self._save_meta()

        log.info(
            "Documents added to FAISS",
            added=len(new_docs),
        )

        return len(new_docs)


# =============================================================================
# DATA INGESTION - PURPOSE & FLOW
# =============================================================================
#
# Purpose:
# Converts uploaded documents into a searchable FAISS retriever for the RAG
# pipeline. File handling and model loading are delegated to reusable utilities.
#
# Flow:
#
#   Uploaded Files
#        │
#        ▼
#   file_io.py
#   save_uploaded_files()
#        │
#        ▼
#   document_ops.py
#   load_documents()
#        │
#        ▼
#   Split into Chunks
#        │
#        ▼
#   model_loader.py
#   load_embeddings()
#        │
#        ▼
#   FaissManager
#        │
#        ├── Existing index -> Load FAISS
#        │
#        └── New index      -> Create FAISS
#        │
#        ▼
#   Add Only New Chunks
#        │
#        ▼
#   FAISS Vector Store
#        │
#        ▼
#   Retriever (Similarity / MMR)
#        │
#        ▼
#   RAG / Question-Answering Pipeline
#
# =============================================================================