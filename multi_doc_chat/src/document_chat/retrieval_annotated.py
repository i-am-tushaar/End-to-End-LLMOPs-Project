"""
retrieval.py
------------

Retrieval and answer-generation layer of the conversational RAG application.

This file is used after `data_ingestion.py` has loaded documents, split them
into chunks, created embeddings, and stored those vectors in a FAISS index.

Main responsibilities:
    1. Load the saved FAISS index.
    2. Create a LangChain retriever.
    3. Rewrite follow-up questions using chat history.
    4. Retrieve relevant document chunks.
    5. Build context for the QA prompt.
    6. Generate and validate the final LLM answer.

High-level relationship:

    data_ingestion.py
          |
          v
    Saved FAISS index
          |
          v
    retrieval.py
          |
          v
    Relevant chunks -> LLM -> Final answer
"""

import sys
import os
from operator import itemgetter
from typing import List, Optional, Dict, Any

from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS

from multi_doc_chat.utils.model_loader import ModelLoader
from multi_doc_chat.exception.custom_exception import DocumentPortalException
from multi_doc_chat.logger import GLOBAL_LOGGER as log
from multi_doc_chat.prompts.prompt_library import PROMPT_REGISTRY
from multi_doc_chat.model.models import PromptType, ChatAnswer
from pydantic import ValidationError


class ConversationalRAG:
    """
    Manage the conversational Retrieval-Augmented Generation (RAG) pipeline.

    The class connects the main retrieval components:

        User question
            -> contextualize question using chat history
            -> search FAISS
            -> retrieve relevant chunks
            -> build QA prompt
            -> LLM
            -> final answer

    The retriever uses lazy initialization. Therefore, this object can be
    created before the FAISS index is loaded.

    Args:
        session_id: Optional identifier for the current conversation/session.
        retriever: Optional pre-built LangChain retriever.

    Example:
        rag = ConversationalRAG(session_id="abc")
        rag.load_retriever_from_faiss(
            index_path="faiss_index/abc",
            k=5,
            index_name="index",
        )
        answer = rag.invoke("What is ...?", chat_history=[])
    """

    def __init__(self, session_id: Optional[str], retriever=None):
        """
        Initialize the RAG service, LLM, prompts, and optional retriever.

        If a retriever is supplied, the LCEL chain is built immediately.
        Otherwise, `load_retriever_from_faiss()` must be called before
        `invoke()`.
        """
        try:
            self.session_id = session_id

            # Load the configured LLM once. ModelLoader hides provider-specific
            # logic, so this class does not need to know whether the model is
            # coming from Google, Groq, or another configured provider.
            self.llm = self._load_llm()
            self.contextualize_prompt: ChatPromptTemplate = PROMPT_REGISTRY[
                PromptType.CONTEXTUALIZE_QUESTION.value
            ]
            self.qa_prompt: ChatPromptTemplate = PROMPT_REGISTRY[
                PromptType.CONTEXT_QA.value
            ]

            # Lazy initialization:
            # The retriever may not be available when this object is created.
            # `self.chain` is therefore built only after a retriever exists.
            self.retriever = retriever
            self.chain = None
            if self.retriever is not None:
                self._build_lcel_chain()

            log.info("ConversationalRAG initialized", session_id=self.session_id)
        except Exception as e:
            log.error("Failed to initialize ConversationalRAG", error=str(e))
            raise DocumentPortalException("Initialization error in ConversationalRAG", sys)

    # ---------- Public API ----------

    def load_retriever_from_faiss(
        self,
        index_path: str,
        k: int = 5,
        index_name: str = "index",
        search_type: str = "mmr",
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        search_kwargs: Optional[Dict[str, Any]] = None,
    ):
        """
        Load FAISS vectorstore from disk and build retriever + LCEL chain.
        
        Args:
            index_path: Path to FAISS index directory
            k: Number of documents to return
            index_name: Name of the index file
            search_type: Type of search ("similarity", "mmr", "similarity_score_threshold")
            fetch_k: Number of documents to fetch before MMR re-ranking (only for MMR)
            lambda_mult: Diversity parameter for MMR (0=max diversity, 1=max relevance)
            search_kwargs: Custom search kwargs (overrides other parameters if provided)
        """
        try:
            if not os.path.isdir(index_path):
                raise FileNotFoundError(f"FAISS index directory not found: {index_path}")

            # Load the embedding model that is compatible with the vectors
            # created during the data-ingestion stage.
            embeddings = ModelLoader().load_embeddings()

            # Load the FAISS vector index previously saved by data_ingestion.py.
            vectorstore = FAISS.load_local(
                index_path,
                embeddings,
                index_name=index_name,
                # FAISS metadata is deserialized from disk. Only load an
                # index that was created by your application or another
                # trusted source.
                allow_dangerous_deserialization=True,
            )

            # Build default retrieval settings unless custom settings were
            # explicitly supplied by the caller.
            if search_kwargs is None:
                search_kwargs = {"k": k}
                if search_type == "mmr":
                    search_kwargs["fetch_k"] = fetch_k
                    search_kwargs["lambda_mult"] = lambda_mult

            # Convert the FAISS vector store into LangChain's standard
            # retriever interface so it can be plugged directly into LCEL.
            self.retriever = vectorstore.as_retriever(
                search_type=search_type, search_kwargs=search_kwargs
            )
            self._build_lcel_chain()

            log.info(
                "FAISS retriever loaded successfully",
                index_path=index_path,
                index_name=index_name,
                search_type=search_type,
                k=k,
                fetch_k=fetch_k if search_type == "mmr" else None,
                lambda_mult=lambda_mult if search_type == "mmr" else None,
                session_id=self.session_id,
            )
            return self.retriever

        except Exception as e:
            log.error("Failed to load retriever from FAISS", error=str(e))
            raise DocumentPortalException("Loading error in ConversationalRAG", sys)

    def invoke(self, user_input: str, chat_history: Optional[List[BaseMessage]] = None) -> str:
        """
        Run one user question through the complete conversational RAG chain.

        Args:
            user_input: Current question asked by the user.
            chat_history: Previous LangChain chat messages.

        Returns:
            Validated answer generated by the LLM.

        Raises:
            DocumentPortalException: If the chain is unavailable or execution
            fails.
        """
        try:
            if self.chain is None:
                raise DocumentPortalException(
                    "RAG chain not initialized. Call load_retriever_from_faiss() before invoke().", sys
                )
            # Use an empty history for the first message in a conversation.
            chat_history = chat_history or []

            # These keys are consumed by itemgetter() inside the LCEL chain.
            payload = {
                "input": user_input,
                "chat_history": chat_history,
            }

            # Execute the complete pipeline:
            # rewrite question -> retrieve context -> QA prompt -> LLM.
            answer = self.chain.invoke(payload)
            if not answer:
                log.warning(
                    "No answer generated", user_input=user_input, session_id=self.session_id
                )
                return "no answer generated."
            # Validate the generated response with the project's Pydantic
            # model. Any constraints defined in ChatAnswer are applied here.
            try:
                validated = ChatAnswer(answer=str(answer))
                answer = validated.answer
            except ValidationError as ve:
                log.error("Invalid chat answer", error=str(ve))
                raise DocumentPortalException("Invalid chat answer", sys)
            log.info(
                "Chain invoked successfully",
                session_id=self.session_id,
                user_input=user_input,
                answer_preview=str(answer)[:150],
            )
            return answer
        except Exception as e:
            log.error("Failed to invoke ConversationalRAG", error=str(e))
            raise DocumentPortalException("Invocation error in ConversationalRAG", sys)

    # ---------- Internals ----------

    def _load_llm(self):
        """
        Load and return the configured LLM through ModelLoader.

        Keeping model-loading logic in ModelLoader makes this retrieval class
        independent of the actual LLM provider.
        """
        try:
            llm = ModelLoader().load_llm()
            if not llm:
                raise ValueError("LLM could not be loaded")
            log.info("LLM loaded successfully", session_id=self.session_id)
            return llm
        except Exception as e:
            log.error("Failed to load LLM", error=str(e))
            raise DocumentPortalException("LLM loading error in ConversationalRAG", sys)

    @staticmethod
    def _format_docs(docs) -> str:
        """
        Combine retrieved document chunks into one context string.

        LangChain retrievers return Document objects. Their actual text is
        normally stored in `page_content`. The QA prompt expects plain text,
        so all retrieved chunks are joined with blank lines.

        Example:
            ["Chunk A", "Chunk B"]
                ->
            "Chunk A\\n\\nChunk B"
        """
        return "\n\n".join(
            getattr(d, "page_content", str(d))
            for d in docs
        )

    def _build_lcel_chain(self):
        """
        Build the LangChain Expression Language (LCEL) RAG pipeline.

        Stage 1:
            current question + chat history
                -> contextualization prompt
                -> LLM
                -> standalone question
                -> retriever

        Stage 2:
            retrieved context + original question + chat history
                -> QA prompt
                -> LLM
                -> final string answer

        In LCEL, the `|` operator pipes the output of one component into the
        next component.
        """
        try:
            if self.retriever is None:
                raise DocumentPortalException("No retriever set before building chain", sys)

            # STEP 1: Rewrite the user's question using chat history.
            #
            # Example:
            #   History: "We are discussing transformers."
            #   User:    "Who invented them?"
            #
            # The rewritten standalone question can become:
            #   "Who invented transformers?"
            #
            # itemgetter("input") extracts payload["input"] and
            # itemgetter("chat_history") extracts payload["chat_history"].
            question_rewriter = (
                {"input": itemgetter("input"), "chat_history": itemgetter("chat_history")}
                | self.contextualize_prompt
                | self.llm
                | StrOutputParser()
            )

            # STEP 2: Search FAISS using the rewritten standalone question.
            #
            # Flow:
            # standalone question
            #     -> retriever
            #     -> List[Document]
            #     -> _format_docs()
            #     -> one context string
            retrieve_docs = question_rewriter | self.retriever | self._format_docs

            # STEP 3: Generate the final answer.
            #
            # The QA prompt receives:
            #   context      = text retrieved from FAISS
            #   input        = original user question
            #   chat_history = previous conversation
            self.chain = (
                {
                    "context": retrieve_docs,
                    "input": itemgetter("input"),
                    "chat_history": itemgetter("chat_history"),
                }
                | self.qa_prompt
                | self.llm
                | StrOutputParser()
            )

            log.info("LCEL graph built successfully", session_id=self.session_id)
        except Exception as e:
            log.error("Failed to build LCEL chain", error=str(e), session_id=self.session_id)
            raise DocumentPortalException("Failed to build LCEL chain", sys)

# ============================================================================
# RETRIEVAL.PY - COMPLETE FLOW
# ============================================================================
#
# BEFORE THIS FILE: data_ingestion.py
#
#   Documents
#      |
#      v
#   Load documents
#      |
#      v
#   Split into chunks
#      |
#      v
#   Create embeddings
#      |
#      v
#   Store vectors in FAISS
#      |
#      v
#   [Saved FAISS Index]
#
#
# THIS FILE: retrieval.py
#
#   [Saved FAISS Index]
#           |
#           v
#   load_retriever_from_faiss()
#           |
#           |-- load embedding model
#           |-- load FAISS index
#           |-- configure similarity/MMR search
#           |-- convert vector store into retriever
#           |
#           v
#   _build_lcel_chain()
#           |
#           v
#   User Question + Chat History
#           |
#           v
#   Contextualization Prompt
#           |
#           v
#          LLM
#           |
#           v
#   Standalone/Rewritten Question
#           |
#           v
#      FAISS Retriever
#           |
#           v
#   Relevant Document Chunks
#           |
#           v
#       _format_docs()
#           |
#           v
#    Combined Context Text
#           |
#           +-----------------------------+
#           |                             |
#           v                             v
#     Original Question              Chat History
#           |                             |
#           +-------------+---------------+
#                         |
#                         v
#                      QA Prompt
#                         |
#                         v
#                        LLM
#                         |
#                         v
#                 StrOutputParser()
#                         |
#                         v
#                   ChatAnswer
#                    Validation
#                         |
#                         v
#                    Final Answer
#
#
# SIMPLE SUMMARY
# --------------
#
# 1. data_ingestion.py creates and saves the FAISS vector index.
# 2. retrieval.py loads that saved index.
# 3. A follow-up question is rewritten using previous chat history.
# 4. The rewritten question is used to search FAISS.
# 5. FAISS returns the most relevant document chunks.
# 6. Those chunks are combined into a context string.
# 7. Context + original question + chat history go into the QA prompt.
# 8. The LLM generates the final answer.
# 9. ChatAnswer validates the response before it is returned.
#
#
# LCEL PIPE OPERATOR
# ------------------
#
#     A | B | C
#
# means:
#
#     A output -> B input -> B output -> C input
#
# Therefore:
#
#     question_rewriter | self.retriever | self._format_docs
#
# means:
#
#     rewrite question
#          ->
#     retrieve relevant chunks
#          ->
#     convert retrieved chunks into context text
#
# ============================================================================

