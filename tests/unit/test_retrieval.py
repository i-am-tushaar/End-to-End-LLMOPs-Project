"""
Unit tests for retrieval.py

Purpose:
- Test ConversationalRAG initialization.
- Test FAISS retriever loading and configuration.
- Test answer generation and error handling.
- Test document formatting and LCEL chain construction.
"""

from unittest.mock import MagicMock, patch

import pytest

from multi_doc_chat.src.document_chat.retrieval import ConversationalRAG
from multi_doc_chat.exception.custom_exception import DocumentPortalException


# ---------------------------------------------------------
# 1. Test successful initialization
# ---------------------------------------------------------
@patch("multi_doc_chat.src.document_chat.retrieval.ModelLoader")
def test_conversational_rag_initialization(mock_model_loader):
    # Simulate successfully loading an LLM without calling a real model.
    mock_model_loader.return_value.load_llm.return_value = MagicMock()

    # Initialize RAG without a retriever.
    rag = ConversationalRAG(session_id="test-session")

    # Verify the session and initial state.
    assert rag.session_id == "test-session"
    assert rag.llm is not None
    assert rag.retriever is None
    assert rag.chain is None
    assert rag.last_ai_message is None
    assert rag.last_usage == {}


# ---------------------------------------------------------
# 2. Test LLM loading failure during initialization
# ---------------------------------------------------------
@patch("multi_doc_chat.src.document_chat.retrieval.ModelLoader")
def test_initialization_fails_when_llm_cannot_load(mock_model_loader):
    # Simulate an LLM loading failure.
    mock_model_loader.return_value.load_llm.return_value = None

    # Initialization should wrap the failure in a custom exception.
    with pytest.raises(DocumentPortalException):
        ConversationalRAG(session_id="test-session")


# ---------------------------------------------------------
# 3. Test formatting LangChain documents
# ---------------------------------------------------------
def test_format_docs_combines_document_content():
    # Create mock documents with known page content.
    doc1 = MagicMock()
    doc1.page_content = "First document"

    doc2 = MagicMock()
    doc2.page_content = "Second document"

    # Format the documents into one string.
    result = ConversationalRAG._format_docs([doc1, doc2])

    # Documents should be separated by two newline characters.
    assert result == "First document\n\nSecond document"


# ---------------------------------------------------------
# 4. Test formatting an empty document list
# ---------------------------------------------------------
def test_format_docs_with_empty_list():
    # No documents should produce an empty string.
    assert ConversationalRAG._format_docs([]) == ""


# ---------------------------------------------------------
# 5. Test invoke when the chain is not initialized
# ---------------------------------------------------------
@patch("multi_doc_chat.src.document_chat.retrieval.ModelLoader")
def test_invoke_without_initialized_chain(mock_model_loader):
    # Initialize RAG, but don't load a retriever or build a chain.
    mock_model_loader.return_value.load_llm.return_value = MagicMock()
    rag = ConversationalRAG(session_id="test-session")

    # Invoking an uninitialized chain should raise the custom exception.
    with pytest.raises(DocumentPortalException):
        rag.invoke("What is RAG?")


# ---------------------------------------------------------
# 6. Test a successful answer
# ---------------------------------------------------------
@patch("multi_doc_chat.src.document_chat.retrieval.ModelLoader")
def test_invoke_returns_valid_answer(mock_model_loader):
    # Mock the LLM so no real model is called.
    mock_model_loader.return_value.load_llm.return_value = MagicMock()
    rag = ConversationalRAG(session_id="test-session")

    # Replace the chain with a mock that returns a valid answer.
    rag.chain = MagicMock()
    rag.chain.invoke.return_value = "RAG retrieves relevant documents."

    # Invoke the RAG pipeline with a user question.
    result = rag.invoke("What is RAG?")

    # Verify the answer and the payload passed to the chain.
    assert result == "RAG retrieves relevant documents."
    rag.chain.invoke.assert_called_once_with(
        {
            "input": "What is RAG?",
            "chat_history": [],
        }
    )


# ---------------------------------------------------------
# 7. Test when the chain returns no answer
# ---------------------------------------------------------
@patch("multi_doc_chat.src.document_chat.retrieval.ModelLoader")
def test_invoke_returns_fallback_for_empty_answer(mock_model_loader):
    # Initialize RAG with a mocked LLM.
    mock_model_loader.return_value.load_llm.return_value = MagicMock()
    rag = ConversationalRAG(session_id="test-session")

    # Simulate the chain returning an empty answer.
    rag.chain = MagicMock()
    rag.chain.invoke.return_value = ""

    # The method should return its documented fallback message.
    result = rag.invoke("What is RAG?")

    assert result == "no answer generated."


# ---------------------------------------------------------
# 8. Test invalid answer handling
# ---------------------------------------------------------
@patch("multi_doc_chat.src.document_chat.retrieval.ModelLoader")
def test_invoke_rejects_invalid_answer(mock_model_loader):
    # Initialize RAG without a real model.
    mock_model_loader.return_value.load_llm.return_value = MagicMock()
    rag = ConversationalRAG(session_id="test-session")

    # ChatAnswer validates the answer; a non-string value is converted
    # to text by invoke(), so use an overlong answer to test validation.
    rag.chain = MagicMock()
    rag.chain.invoke.return_value = "A" * 10001

    # Invalid answer length should produce DocumentPortalException.
    with pytest.raises(DocumentPortalException):
        rag.invoke("What is RAG?")


# ---------------------------------------------------------
# 9. Test missing FAISS index directory
# ---------------------------------------------------------
@patch("multi_doc_chat.src.document_chat.retrieval.ModelLoader")
def test_load_retriever_fails_for_missing_directory(mock_model_loader):
    # Initialize RAG with a mocked LLM.
    mock_model_loader.return_value.load_llm.return_value = MagicMock()
    rag = ConversationalRAG(session_id="test-session")

    # A directory that doesn't exist should cause a custom exception.
    with pytest.raises(DocumentPortalException):
        rag.load_retriever_from_faiss(
            index_path="nonexistent_faiss_directory"
        )


# ---------------------------------------------------------
# 10. Test invoking the chain with chat history
# ---------------------------------------------------------
@patch("multi_doc_chat.src.document_chat.retrieval.ModelLoader")
def test_invoke_passes_chat_history(mock_model_loader):
    # Initialize RAG with a mocked LLM.
    mock_model_loader.return_value.load_llm.return_value = MagicMock()
    rag = ConversationalRAG(session_id="test-session")

    # Set up a fake chain that returns a valid answer.
    rag.chain = MagicMock()
    rag.chain.invoke.return_value = "The answer is 42."

    history = []
    result = rag.invoke("What is the answer?", chat_history=history)

    # Verify that chat history reaches the chain unchanged.
    assert result == "The answer is 42."
    rag.chain.invoke.assert_called_once_with(
        {
            "input": "What is the answer?",
            "chat_history": history,
        }
    )
