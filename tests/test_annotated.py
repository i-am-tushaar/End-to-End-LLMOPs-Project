import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

from multi_doc_chat.src.document_ingestion.data_ingestion import ChatIngestor
from multi_doc_chat.src.document_chat.retrieval import ConversationalRAG

# =============================================================================
# Load environment variables from the .env file
# =============================================================================
load_dotenv()


def test_document_ingestion_and_rag():
    """
    Test the complete RAG pipeline.

    Workflow:
    1. Load PDF documents.
    2. Create embeddings.
    3. Store embeddings in a FAISS vector database.
    4. Load the FAISS index.
    5. Start an interactive conversational RAG chatbot.
    """

    try:
        # =====================================================================
        # List of documents to ingest
        #
        # Use a raw string (r"...") for Windows paths to avoid escape sequence
        # warnings such as "\A".
        # =====================================================================
        test_files = [
            r"F:\AI Projects\End-to-End-LLMOPs-Project\data\Attention_is_all_you_need.pdf",
        ]

        uploaded_files = []

        # =====================================================================
        # Open all valid files
        # =====================================================================
        for file_path in test_files:

            if Path(file_path).exists():
                uploaded_files.append(open(file_path, "rb"))

            else:
                print(f"❌ File does not exist: {file_path}")

        # Stop execution if no valid documents were found
        if not uploaded_files:
            print("❌ No valid files to upload.")
            sys.exit(1)

        # =====================================================================
        # Initialize the document ingestion pipeline
        #
        # temp_base:
        #     Temporary directory used during document processing.
        #
        # faiss_base:
        #     Base directory where FAISS indexes are stored.
        #
        # use_session_dirs=True:
        #     Creates a unique folder for every ingestion session.
        # =====================================================================
        ci = ChatIngestor(
            temp_base="data",
            faiss_base="faiss_index",
            use_session_dirs=True,
        )

        # =====================================================================
        # Build the retriever
        #
        # search_type="mmr"
        #     Uses Maximal Marginal Relevance retrieval.
        #
        # chunk_size
        #     Number of characters per chunk.
        #
        # chunk_overlap
        #     Overlap between consecutive chunks.
        #
        # k
        #     Number of final documents returned.
        #
        # fetch_k
        #     Number of candidate documents retrieved before MMR.
        #
        # lambda_mult
        #     Controls diversity.
        #
        #         0.0 -> Maximum diversity
        #         1.0 -> Maximum relevance
        #         0.5 -> Balanced
        # =====================================================================
        retriever = ci.built_retriver(
            uploaded_files,
            chunk_size=200,
            chunk_overlap=20,
            k=5,
            search_type="mmr",
            fetch_k=20,
            lambda_mult=0.5,
        )

        # ---------------------------------------------------------------------
        # Alternative retrieval strategy
        # ---------------------------------------------------------------------
        # retriever = ci.built_retriver(
        #     uploaded_files,
        #     chunk_size=200,
        #     chunk_overlap=20,
        #     k=5,
        #     search_type="similarity",
        # )

        # =====================================================================
        # Close all opened file handles
        # =====================================================================
        for file in uploaded_files:

            try:
                file.close()

            except Exception:
                pass

        # =====================================================================
        # Get the generated session ID
        # =====================================================================
        session_id = ci.session_id

        # Location of the generated FAISS index
        index_dir = os.path.join("faiss_index", session_id)

        # =====================================================================
        # Initialize Conversational RAG
        # =====================================================================
        rag = ConversationalRAG(session_id=session_id)

        # =====================================================================
        # Load the previously created FAISS index
        # =====================================================================
        rag.load_retriever_from_faiss(
            index_path=index_dir,
            k=5,
            index_name=os.getenv("FAISS_INDEX_NAME", "index"),
            search_type="mmr",
            fetch_k=20,
            lambda_mult=0.5,
        )

        # =====================================================================
        # Conversation history
        #
        # This stores previous user and assistant messages so the LLM remembers
        # earlier questions during the chat.
        # =====================================================================
        chat_history = []

        print("\n==============================================")
        print(" Interactive Multi-Document RAG Chat Started")
        print(" Type 'exit' to quit")
        print("==============================================\n")

        while True:

            try:
                user_input = input("You: ").strip()

            except (EOFError, KeyboardInterrupt):
                print("\nExiting chat...")
                break

            # Ignore empty inputs
            if not user_input:
                continue

            # Exit commands
            if user_input.lower() in {"exit", "quit", "q", ":q"}:
                print("Goodbye!")
                break

            # ================================================================
            # Invoke the RAG pipeline
            # ================================================================
            answer = rag.invoke(
                user_input,
                chat_history=chat_history,
            )

            print("Assistant:", answer)

            # ================================================================
            # Store conversation history
            #
            # This allows the chatbot to answer follow-up questions while
            # remembering previous interactions.
            # ================================================================
            chat_history.append(HumanMessage(content=user_input))
            chat_history.append(AIMessage(content=answer))

    except Exception as e:

        print(f"\n❌ Test failed: {str(e)}")
        sys.exit(1)


# =============================================================================
# Entry point
# =============================================================================
if __name__ == "__main__":
    test_document_ingestion_and_rag()


# =============================================================================
# TEST.PY - COMPLETE FLOW EXPLANATION
# =============================================================================
#
# PURPOSE OF THIS FILE
# --------------------
# This file is used to manually test the complete RAG (Retrieval-Augmented
# Generation) pipeline from document ingestion to conversational question
# answering.
#
# Instead of calling the FastAPI endpoints, this script directly interacts
# with the backend classes. It is mainly used during development and debugging
# to verify that every module works correctly.
#
#
# =============================================================================
# BEFORE THIS FILE
# =============================================================================
#
# 1. User creates a .env file with all required API keys.
#
# 2. Required packages are installed using uv.
#
# 3. PDF documents are placed inside the data folder.
#
# Example:
#
# data/
# ├── Attention_is_all_you_need.pdf
# ├── RAG.pdf
# └── LLM.pdf
#
#
# =============================================================================
# WHAT HAPPENS INSIDE THIS FILE
# =============================================================================
#
# STEP 1
# -------
# Load environment variables.
#
# load_dotenv()
#
# Loads API keys such as:
#
# GOOGLE_API_KEY
# GROQ_API_KEY
# OPENAI_API_KEY
#
#
# STEP 2
# -------
# Define the PDF documents.
#
# test_files = [...]
#
# These documents will be indexed into the vector database.
#
#
# STEP 3
# -------
# Validate that every file exists.
#
# If any file does not exist,
# it prints an error and skips it.
#
#
# STEP 4
# -------
# Create ChatIngestor.
#
# ChatIngestor performs:
#
# • Document Loading
# • Text Splitting
# • Embedding Generation
# • FAISS Vector Store Creation
#
#
# STEP 5
# -------
# Build Retriever.
#
# built_retriver(...)
#
# This internally performs:
#
# PDF
#   ↓
# Load Pages
#   ↓
# Split into Chunks
#   ↓
# Create Embeddings
#   ↓
# Store Embeddings in FAISS
#   ↓
# Return Retriever
#
#
# STEP 6
# -------
# Close opened PDF files.
#
# Always close file handles to avoid
# memory leaks.
#
#
# STEP 7
# -------
# Read generated session_id.
#
# Every ingestion creates a unique folder.
#
# Example:
#
# faiss_index/
# └── a12bc34d/
#       index.faiss
#       index.pkl
#
#
# STEP 8
# -------
# Create ConversationalRAG object.
#
# This class loads the saved FAISS vector store.
#
#
# STEP 9
# -------
# Load Retriever from FAISS.
#
# rag.load_retriever_from_faiss(...)
#
# This reconnects the chatbot with the
# previously stored embeddings.
#
#
# STEP 10
# --------
# Start interactive chatbot.
#
# while True:
#
# User can continuously ask questions.
#
#
# STEP 11
# --------
# User question.
#
# Example:
#
# "What is Attention?"
#
#
# STEP 12
# --------
# Retrieve relevant chunks.
#
# Retriever searches the FAISS index.
#
#
# STEP 13
# --------
# Relevant chunks +
# User Question
#
# are inserted into the Prompt Template.
#
#
# STEP 14
# --------
# Prompt is sent to the LLM.
#
# Example:
#
# Gemini
# Groq
# OpenAI
#
#
# STEP 15
# --------
# LLM generates final answer.
#
#
# STEP 16
# --------
# Save conversation history.
#
# chat_history.append(HumanMessage(...))
#
# chat_history.append(AIMessage(...))
#
# This enables multi-turn conversations.
#
#
# =============================================================================
# COMPLETE DATA FLOW
# =============================================================================
#
#                User Starts test.py
#                        │
#                        ▼
#               Load Environment Variables
#                        │
#                        ▼
#                Read PDF Documents
#                        │
#                        ▼
#               Validate File Paths
#                        │
#                        ▼
#                 Create ChatIngestor
#                        │
#                        ▼
#                Load PDF Documents
#                        │
#                        ▼
#                 Split into Chunks
#                        │
#                        ▼
#              Generate Embeddings
#                        │
#                        ▼
#              Store in FAISS Index
#                        │
#                        ▼
#             Save Session Directory
#                        │
#                        ▼
#             Load FAISS Retriever
#                        │
#                        ▼
#          User asks a Question
#                        │
#                        ▼
#       Retriever finds relevant chunks
#                        │
#                        ▼
#     Retrieved Context + User Question
#                        │
#                        ▼
#            Prompt Template
#                        │
#                        ▼
#                    LLM
#                        │
#                        ▼
#               Generated Answer
#                        │
#                        ▼
#          Store Conversation History
#                        │
#                        ▼
#          Wait for Next User Question
#
#
# =============================================================================
# FILE RESPONSIBILITIES
# =============================================================================
#
# ✓ Load environment variables
# ✓ Read PDF documents
# ✓ Validate file paths
# ✓ Build FAISS vector store
# ✓ Create retriever
# ✓ Load retriever
# ✓ Start conversational chatbot
# ✓ Maintain chat history
# ✓ Test complete RAG pipeline
#
#
# =============================================================================
# WHY THIS FILE IS NEEDED
# =============================================================================
#
# During development, testing the complete pipeline through the frontend or
# FastAPI API is slow and inconvenient.
#
# This script provides a quick way to verify that:
#
# • Document loading works
# • Chunking works
# • Embedding generation works
# • FAISS indexing works
# • Retrieval works
# • Prompt creation works
# • LLM response generation works
# • Multi-turn conversation works
#
# before integrating everything with the frontend.
#
#
# =============================================================================
# SIMPLE SUMMARY
# =============================================================================
#
# test.py acts as a local testing playground for the complete RAG pipeline.
# It ingests documents, creates a vector database, loads the retriever,
# starts an interactive chatbot, and verifies that every backend component
# is working correctly before deployment.
#
# =============================================================================