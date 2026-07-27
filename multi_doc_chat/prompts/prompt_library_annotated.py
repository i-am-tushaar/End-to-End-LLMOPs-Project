"""
prompt_library.py
-----------------

This module stores the prompt templates used by the conversational RAG
retrieval pipeline.

Why keep prompts in a separate file?
    - Retrieval logic stays clean.
    - Prompts can be changed without modifying retrieval.py.
    - Multiple prompts can be managed from one central location.
    - Prompts can be reused across different parts of the application.

This file defines two main prompts:

    1. contextualize_question_prompt
       Rewrites a follow-up question into a standalone question by using
       previous chat history.

    2. context_qa_prompt
       Generates the final answer using the document context retrieved from
       the vector database.

Both prompts are stored inside PROMPT_REGISTRY so retrieval.py can select
them by name.
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


# ============================================================================
# 1. CONTEXTUALIZE / QUESTION-REWRITING PROMPT
# ============================================================================

# This prompt is used BEFORE document retrieval.
#
# Its job is NOT to answer the question.
# Its only job is to understand references in the current question by looking
# at the previous conversation and then create a standalone question.
#
# Why is this needed?
#
# Example conversation:
#
#   User: "Hello there, I want to study about RAG."
#   AI:   "Sure..."
#   User: "What is the full form of it?"
#
# Searching the vector database directly for:
#
#   "What is the full form of it?"
#
# is weak because "it" has no meaning without the previous conversation.
#
# This prompt can rewrite it as:
#
#   "What is the full form of RAG?"
#
# That standalone question is much better for retrieval.

contextualize_question_prompt = ChatPromptTemplate.from_messages([
    # SYSTEM MESSAGE
    #
    # The system message gives the LLM its main instruction.
    # Here we explicitly tell it to REWRITE the question, not answer it.
    (
        "system",
        (
            "Given a conversation history and the most recent user query, "
            "rewrite the query as a standalone question "
            "that makes sense without relying on the previous context. "
            "Do not provide an answer—only reformulate the "
            "question if necessary; otherwise, return it unchanged."
        ),
    ),

    # CHAT HISTORY PLACEHOLDER
    #
    # MessagesPlaceholder dynamically inserts previous conversation messages.
    #
    # For example:
    #
    #   HumanMessage("I want to study about RAG")
    #   AIMessage("Sure, what would you like to know?")
    #
    # `retrieval.py` supplies this value using the "chat_history" key.
    MessagesPlaceholder("chat_history"),

    # CURRENT USER QUESTION
    #
    # {input} is a template variable.
    # retrieval.py replaces it with the latest user question.
    #
    # Example:
    #   {input} -> "What is the full form of it?"
    ("human", "{input}"),
])


# ============================================================================
# 2. CONTEXT-BASED QUESTION ANSWERING PROMPT
# ============================================================================

# This prompt is used AFTER the retriever has found relevant document chunks.
#
# Its job is to generate the final answer using the retrieved context.
#
# Example:
#
#   User question:
#       "What is the full form of RAG?"
#
#   Retrieved context:
#       "RAG stands for Retrieval-Augmented Generation..."
#
#   This prompt sends that context, the chat history, and the user's original
#   question to the LLM so it can generate the final answer.

context_qa_prompt = ChatPromptTemplate.from_messages([
    # SYSTEM MESSAGE
    #
    # This defines the rules for final answer generation:
    #
    #   1. Use only the supplied retrieved context.
    #   2. Do not invent information.
    #   3. Say "I don't know." if the answer is absent.
    #   4. Keep the response concise.
    #
    # {context} is dynamically replaced by the text returned from the
    # FAISS retriever and formatted by retrieval.py.
    (
        "system",
        (
            "You are an assistant designed to answer questions using the "
            "provided context. Rely only on the retrieved "
            "information to form your response. If the answer is not found "
            "in the context, respond with 'I don't know.' "
            "Keep your answer concise and no longer than three sentences."
            "\n\n{context}"
        ),
    ),

    # Insert previous chat messages so the final answer can still preserve
    # conversational continuity.
    MessagesPlaceholder("chat_history"),

    # Insert the user's current/original question.
    ("human", "{input}"),
])


# ============================================================================
# 3. CENTRAL PROMPT REGISTRY
# ============================================================================

# PROMPT_REGISTRY provides one central dictionary containing all prompts.
#
# Instead of importing every prompt separately, retrieval.py can request a
# prompt by its key.
#
# Example used conceptually in retrieval.py:
#
#   PROMPT_REGISTRY["contextualize_question"]
#       -> contextualize_question_prompt
#
#   PROMPT_REGISTRY["context_qa"]
#       -> context_qa_prompt
#
# This makes the project easier to maintain and extend. If another prompt is
# needed later, it can be registered here.

PROMPT_REGISTRY = {
    "contextualize_question": contextualize_question_prompt,
    "context_qa": context_qa_prompt,
}


# ============================================================================
# EXAMPLE CONVERSATION
# ============================================================================
#
# 1. User:
#       "Hello there, I want to study about RAG."
#
# 2. User:
#       "What is the full form of it?"
#
# Because the second question contains "it", it depends on chat history.
#
# contextualize_question_prompt:
#
#       "What is the full form of it?"
#                    +
#              chat history
#                    |
#                    v
#       "What is the full form of RAG?"
#
# That rewritten question can now be used for vector search.


# ============================================================================
# PROMPT_LIBRARY.PY - COMPLETE FLOW DIAGRAM
# ============================================================================
#
#                       USER
#                        |
#                        v
#               Current User Question
#                        +
#                   Chat History
#                        |
#                        v
#       +------------------------------------+
#       | contextualize_question_prompt      |
#       |                                    |
#       | Purpose: understand follow-up      |
#       | questions and rewrite them into    |
#       | standalone questions               |
#       +------------------------------------+
#                        |
#                        v
#               Standalone Question
#
# Example:
#
#       "What is the full form of it?"
#                        |
#                        v
#       "What is the full form of RAG?"
#                        |
#                        v
#                 retrieval.py
#                        |
#                        v
#                 FAISS Retriever
#                        |
#                        v
#              Relevant Document Chunks
#                        |
#                        v
#                 {context}
#                        |
#                        +-------------------------+
#                        |                         |
#                        v                         v
#                 Chat History              User Question
#                        |                         |
#                        +------------+------------+
#                                     |
#                                     v
#                     +-------------------------------+
#                     |       context_qa_prompt       |
#                     |                               |
#                     | Context + question + history  |
#                     | are given to the LLM          |
#                     +-------------------------------+
#                                     |
#                                     v
#                                    LLM
#                                     |
#                                     v
#                              Final RAG Answer
#
#
# ============================================================================
# HOW PROMPT_LIBRARY.PY CONNECTS WITH RETRIEVAL.PY
# ============================================================================
#
# prompt_library.py
#       |
#       | provides
#       |
#       +--> contextualize_question_prompt
#       |
#       +--> context_qa_prompt
#       |
#       v
# PROMPT_REGISTRY
#       |
#       v
# retrieval.py
#       |
#       +--> Question Rewriter
#       |       |
#       |       v
#       |    Retriever / FAISS
#       |
#       +--> Retrieved Context
#               |
#               v
#             QA Prompt
#               |
#               v
#              LLM
#               |
#               v
#          Final Answer
#
#
# SIMPLE SUMMARY
# --------------
#
# prompt_library.py does NOT retrieve documents and does NOT directly call
# the LLM.
#
# It only DEFINES and REGISTERS the instructions/prompts that retrieval.py
# uses while building the RAG chain.
#
# Prompt 1:
#     contextualize_question_prompt
#
#     Chat history + current question
#                ->
#     standalone searchable question
#
# Prompt 2:
#     context_qa_prompt
#
#     Retrieved context + chat history + question
#                ->
#     instructions for generating the final answer
#
# PROMPT_REGISTRY:
#
#     Stores both prompts in one place so retrieval.py can access them easily.
#
# ============================================================================
