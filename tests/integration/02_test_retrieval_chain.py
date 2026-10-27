
"""
Integration Test 2: Retrieval Chain Integration

Purpose:
    Verify that ConversationalRAG loads a saved FAISS index,
    retrieves relevant document content, and generates an answer.

What is tested for real:
    * ChatIngestor and FaissManager create and save the FAISS index.
    * ConversationalRAG loads the saved FAISS index from disk.
    * The retriever searches the indexed document content.
    * The RAG chain connects question rewriting, retrieval, and answer generation.
    * The generated answer is returned as a string.

What is replaced:
    * The model loader, through the stub_model_loader fixture
      (see conftest.py). This avoids calling a real embedding or LLM provider.

How to run:
    uv run pytest tests/integration/02_test_retrieval_chain.py -v
"""

import io

from multi_doc_chat.src.document_ingestion.data_ingestion import ChatIngestor
from multi_doc_chat.src.document_chat.retrieval import ConversationalRAG


# Integration Test 2: Retrieval chain loads a saved FAISS index and answers a question.
# Objective: Verify that a document can be indexed, loaded from disk,
# searched by ConversationalRAG, and used to generate an answer.
def test_retrieval_chain_loads_index_and_returns_answer(
    tmp_path, stub_model_loader
):
    """Verify the flow from a saved FAISS index to a generated RAG answer."""

    # Step 1: Prepare a sample document for ingestion.
    # The document contains a clear definition of RAG that we can search for.
    content = (
        "RAG stands for Retrieval-Augmented Generation. "
        "It retrieves relevant documents and uses their context "
        "to help a language model generate an answer."
    )

    # Create an in-memory file and give it a .txt filename.
    # This mimics the file-like object expected by the ingestion pipeline.
    uploaded_file = io.BytesIO(content.encode("utf-8"))
    uploaded_file.name = "rag_guide.txt"

    # Step 2: Initialize ChatIngestor with temporary directories.
    # tmp_path provides an isolated directory for this test, keeping
    # the project's real data and FAISS index folders unchanged.
    ingestor = ChatIngestor(
        temp_base=str(tmp_path / "data"),
        faiss_base=str(tmp_path / "faiss_index"),
        use_session_dirs=True,
        session_id="retrieval_test_session",
    )

    # Step 3: Run the actual ingestion pipeline.
    # This saves the file, loads its contents, splits the document,
    # creates the FAISS index, and saves the index files to disk.
    ingestor.built_retriver(
        uploaded_files=[uploaded_file],
        search_type="similarity",
        k=2,
    )

    # Verify that the saved FAISS index files exist before loading them.
    assert (ingestor.faiss_dir / "index.faiss").exists()
    assert (ingestor.faiss_dir / "index.pkl").exists()

    # Step 4: Initialize ConversationalRAG and load the saved index.
    # The index is loaded from disk rather than reusing the retriever
    # returned by ChatIngestor. This tests the saved-index loading path.
    rag = ConversationalRAG(session_id="retrieval_test_session")

    retriever = rag.load_retriever_from_faiss(
        index_path=str(ingestor.faiss_dir),
        search_type="similarity",
        k=2,
    )

    # Step 5: Verify that the loaded retriever finds relevant content.
    # Ask a question about the definition of RAG.
    retrieved_docs = retriever.invoke("What does RAG stand for?")

    # The retriever must return at least one document.
    assert retrieved_docs

    # At least one retrieved document must contain the expected definition.
    assert any(
        "Retrieval-Augmented Generation" in doc.page_content
        for doc in retrieved_docs
    )

    # Step 6: Verify that the RAG chain generates an answer.
    # ConversationalRAG.invoke() runs the configured chain, which uses
    # the question, retrieved context, and the stubbed LLM.
    answer = rag.invoke("What does RAG stand for?")

    # The answer must be a non-empty string.
    assert isinstance(answer, str)
    assert answer.strip()


# =============================================================================
# INTEGRATION TEST 2 - WORKFLOW
# =============================================================================

# Purpose:
# Demonstrates how document ingestion, FAISS indexing, retrieval,
# and answer generation work together in the RAG pipeline.

# Workflow:
#
# 1. Sample TXT Document
#        |
#        v
# 2. ChatIngestor
#        |
#        v
# 3. Save Uploaded File
#        |
#        v
# 4. Load and Split Document
#        |
#        v
# 5. Generate Embeddings and Create FAISS Index
#        |
#        v
# 6. Save index.faiss and index.pkl to Disk
#        |
#        v
# 7. ConversationalRAG Loads the Saved FAISS Index
#        |
#        v
# 8. User Asks a Question
#        |
#        v
# 9. Retrieve Relevant Document Content
#        |
#        v
# 10. Pass Question and Retrieved Context to the RAG Chain
#        |
#        v
# 11. Stub LLM Generates an Answer
#        |
#        v
# 12. Verify Retrieved Content and Generated Answer
#
# Expected Result:
# The saved FAISS index loads successfully, relevant content is retrieved,
# and ConversationalRAG returns a non-empty answer.
#
# Important:
# The ingestion, FAISS indexing, index loading, and retrieval operations
# run through the actual implementation. The model loader is stubbed
# to avoid real embedding-provider and LLM API calls.
#
# =============================================================================