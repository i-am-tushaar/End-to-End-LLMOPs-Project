"""
Integration Test 1: Document Ingestion Integration

Purpose:
    Verify that ChatIngestor saves a text file, loads its content,
    creates a FAISS index, and returns a working retriever.

What is tested for real:
    * ChatIngestor and FaissManager (the actual implementation)
    * Saving the uploaded file to disk
    * Loading and splitting the document content
    * Creating and saving a real FAISS index (index.faiss and index.pkl)
    * Searching the index through the returned retriever

What is replaced:
    * The model loader, through the stub_model_loader fixture
      (see conftest.py). This keeps the test fast and avoids calling
      a real embedding provider.

How to run:
    uv run pytest tests/integration/test_data_ingestion_integration.py -v
"""

import io

from multi_doc_chat.src.document_ingestion.data_ingestion import ChatIngestor


# Integration Test 1: Document ingestion creates a FAISS index
# Objective: Verify that ChatIngestor accepts an uploaded text file,
# creates a FAISS index on disk (index.faiss and index.pkl), and returns
# a retriever that can find the content of the file.
def test_document_ingestion_creates_faiss_index(
    tmp_path, stub_model_loader
):
    """Verify the full ingestion flow from an uploaded text file to a retriever."""

    # Step 1: Prepare a sample document for ingestion.
    # The text has two clear facts, so the search in Step 5 has
    # something specific to find.
    content = (
        "LLMOps manages the lifecycle of large language models. "
        "RAG retrieves relevant documents to improve generated answers."
    )

    # Create an in memory file and give it a name, so that it looks like
    # a file uploaded through the API. The .txt extension is important
    # because only supported extensions (such as .txt) are saved.
    uploaded_file = io.BytesIO(content.encode("utf-8"))
    uploaded_file.name = "integration_guide.txt"

    # Step 2: Use temporary folders to avoid changing project data.
    # tmp_path is a pytest fixture that gives a fresh folder for each test
    # and removes it afterwards, so the real "data" and "faiss_index"
    # folders in the project are never touched.
    ingestor = ChatIngestor(
        temp_base=str(tmp_path / "data"),
        faiss_base=str(tmp_path / "faiss_index"),
        use_session_dirs=True,
        session_id="integration_test_session",
    )

    # Step 3: Run the actual ingestion pipeline.
    # This saves the file, loads and splits it, builds the FAISS index,
    # and returns a retriever. Plain similarity search is used so that
    # the result does not depend on the MMR diversity settings, and k=2
    # asks for the two best matching chunks.
    retriever = ingestor.built_retriver(
        uploaded_files=[uploaded_file],
        search_type="similarity",
        k=2,
    )

    # Step 4: Verify that the FAISS index was created.
    # FAISS saves two files: index.faiss holds the vectors and
    # index.pkl holds the document store and the id mapping.
    assert (ingestor.faiss_dir / "index.faiss").exists()
    assert (ingestor.faiss_dir / "index.pkl").exists()

    # Step 5: Verify that the retriever can retrieve document content.
    # Ask a question about the second sentence of the file.
    results = retriever.invoke("What does RAG do?")

    # The retriever must return at least one result.
    assert results

    # At least one returned chunk must contain the sentence about RAG,
    # which proves that the content was indexed and can be searched.
    assert any("RAG retrieves relevant documents" in doc.page_content
               for doc in results)


# =============================================================================
# INTEGRATION TEST 1 - WORKFLOW
# =============================================================================

# Purpose:
# Demonstrates how an uploaded text document becomes a searchable
# FAISS index through the actual document ingestion pipeline.

# Workflow:
#
# 1. Prepare a Sample TXT Document
#        |
#        v
# 2. Create an In-Memory Uploaded File
#        |
#        v
# 3. Initialize ChatIngestor
#        |
#        v
# 4. Save the Uploaded File to a Temporary Directory
#        |
#        v
# 5. Load the Document Using load_documents()
#        |
#        v
# 6. Split the Document into Smaller Chunks
#        |
#        v
# 7. Generate Embeddings Using the Stub Model Loader
#        |
#        v
# 8. Create and Save the FAISS Index
#        |
#        v
# 9. Verify index.faiss and index.pkl Exist
#        |
#        v
# 10. Search the Index Through the Returned Retriever
#        |
#        v
# 11. Verify That Relevant Document Content Is Retrieved
#
# Expected Result:
# The document is saved, loaded, split, indexed, and successfully
# searched. The retriever returns content relevant to the user's query.
#
# Important:
# The actual ChatIngestor, FaissManager, file-saving, document-loading,
# chunking, FAISS indexing, and retrieval implementations are exercised.
# The model loader is stubbed to avoid calls to a real embedding provider.
# Temporary directories prevent changes to the project's real data folders.
#
# =============================================================================