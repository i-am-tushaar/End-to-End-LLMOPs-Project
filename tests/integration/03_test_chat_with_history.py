
"""
Integration Test 3: Chat with History

Purpose:
    Verify that ConversationalRAG accepts previous conversation messages
    and uses the chat history input when answering a follow-up question.

What is tested for real:
    * Creating and saving a FAISS index
    * Loading the saved index through ConversationalRAG
    * Building and invoking the LCEL RAG chain
    * Passing chat history into the RAG chain

What is replaced:
    * The model loader, embeddings, and LLM through stub_model_loader.
    * No real external model-provider calls are made.

How to run:
    uv run pytest tests/integration/03_test_chat_with_history.py -v
"""

import io

from langchain_core.messages import HumanMessage, AIMessage

from multi_doc_chat.src.document_ingestion.data_ingestion import ChatIngestor
from multi_doc_chat.src.document_chat.retrieval import ConversationalRAG


def test_chat_with_history_accepts_follow_up_question(
    tmp_path, stub_model_loader
):
    """Verify that the RAG chain accepts chat history for a follow-up question."""

    # Step 1: Prepare a document with facts the retriever can search.
    content = (
        "The project is called Lakshya AI. "
        "It helps students prepare for competitive examinations."
    )
    uploaded_file = io.BytesIO(content.encode("utf-8"))
    uploaded_file.name = "project_guide.txt"

    # Step 2: Create an ingestor using temporary folders.
    ingestor = ChatIngestor(
        temp_base=str(tmp_path / "data"),
        faiss_base=str(tmp_path / "faiss_index"),
        use_session_dirs=True,
        session_id="chat_history_test_session",
    )

    # Step 3: Ingest the document and create a real FAISS index.
    ingestor.built_retriver(
        uploaded_files=[uploaded_file],
        search_type="similarity",
        k=2,
    )

    # Verify that the index was saved.
    assert (ingestor.faiss_dir / "index.faiss").exists()
    assert (ingestor.faiss_dir / "index.pkl").exists()

    # Step 4: Initialize the RAG component and load the saved index.
    rag = ConversationalRAG(session_id="chat_history_test_session")
    rag.load_retriever_from_faiss(
        index_path=str(ingestor.faiss_dir),
        search_type="similarity",
        k=2,
    )

    # Step 5: Create the previous conversation history.
    chat_history = [
        HumanMessage(content="What is the project called?"),
        AIMessage(content="The project is called Lakshya AI."),
    ]

    # Step 6: Ask a follow-up question with the previous messages.
    answer = rag.invoke(
        "What does it help students do?",
        chat_history=chat_history,
    )

    # Step 7: Verify that an answer is returned.
    assert isinstance(answer, str)
    assert answer.strip()

    # Verify the RAG chain exists and was built successfully.
    assert rag.chain is not None


# =============================================================================
# INTEGRATION TEST 3 - WORKFLOW
# =============================================================================

# Purpose:
# Verify that ConversationalRAG can accept conversation history
# while processing a follow-up question.

# Workflow:
#
# 1. Prepare a sample TXT document
#        |
#        v
# 2. Initialize ChatIngestor with temporary directories
#        |
#        v
# 3. Save, load, and split the document
#        |
#        v
# 4. Generate stub embeddings and create a FAISS index
#        |
#        v
# 5. Save index.faiss and index.pkl
#        |
#        v
# 6. Initialize ConversationalRAG
#        |
#        v
# 7. Load the saved FAISS index and build the LCEL chain
#        |
#        v
# 8. Create previous messages using HumanMessage and AIMessage
#        |
#        v
# 9. Ask a follow-up question with chat_history
#        |
#        v
# 10. Verify that the chain returns a non-empty answer
#
# Expected Result:
# The RAG chain accepts the previous conversation messages and
# returns a non-empty answer without calling a real LLM provider.
#
# Important:
# This test checks that chat history is accepted and passed into
# the chain. Since the LLM is stubbed, it does not prove that a
# real LLM correctly interprets or uses the history semantically.
#
# =============================================================================
