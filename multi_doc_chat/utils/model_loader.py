
"""
Centralized loader for API keys, Hugging Face embeddings, and Groq LLM.
"""

import os
import sys

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq

from multi_doc_chat.utils.config_loader import load_config
from multi_doc_chat.logger import GLOBAL_LOGGER as log
from multi_doc_chat.exception.custom_exception import DocumentPortalException


class ApiKeyManager:
    """Loads the Groq API key from environment variables."""

    def __init__(self):
        self.api_keys = {
            "GROQ_API_KEY": os.getenv("GROQ_API_KEY")
        }

        log.info("API key manager initialized")

    def get(self, key: str) -> str:
        """Return the requested API key or raise an error."""
        value = self.api_keys.get(key) or os.getenv(key)

        if not value:
            raise KeyError(f"API key '{key}' is missing")

        return value


class ModelLoader:
    """Loads Hugging Face embeddings and Groq LLM."""

    def __init__(self):

        # Load .env locally. ECS provides environment variables in production.
        if os.getenv("APP_ENV", "development").lower() != "production":
            load_dotenv(override=True)
            log.info("Running in LOCAL mode")
        else:
            log.info("Running in PRODUCTION mode")

        self.config = load_config()
        self.api_keys = ApiKeyManager()

        # Only supported providers.
        self.embedding_provider = "huggingface"
        self.llm_provider = "groq"

        log.info(
            "Selected providers",
            embedding_provider=self.embedding_provider,
            llm_provider=self.llm_provider,
        )

        # Validate the Groq API key.
        self.api_keys.get("GROQ_API_KEY")

    def load_embeddings(self):
        """Load Hugging Face sentence-transformer embeddings."""

        try:
            cfg = self.config["embedding_model"]["huggingface"]
            model = cfg["model_name"]

            log.info(
                "Loading embeddings",
                provider="huggingface",
                model=model,
            )

            return HuggingFaceEmbeddings(
                model_name=model
            )

        except Exception as e:
            log.error("Failed to load embeddings", error=str(e))

            raise DocumentPortalException(
                "Failed to load Hugging Face embeddings", sys
            ) from e

    def load_llm(self):
        """Load the Groq language model."""

        try:
            cfg = self.config["llm"]["groq"]

            model = cfg["model_name"]
            temperature = cfg.get("temperature", 0)
            max_tokens = cfg.get("max_output_tokens", 2048)

            log.info(
                "Loading LLM",
                provider="groq",
                model=model,
            )

            return ChatGroq(
                model=model,
                api_key=self.api_keys.get("GROQ_API_KEY"),
                temperature=temperature,
                max_tokens=max_tokens,
            )

        except Exception as e:
            log.error("Failed to load LLM", error=str(e))

            raise DocumentPortalException(
                "Failed to load Groq LLM", sys
            ) from e


if __name__ == "__main__":

    loader = ModelLoader()

    print("\n--- Testing Hugging Face Embeddings ---")

    embeddings = loader.load_embeddings()
    result = embeddings.embed_query("Hello, how are you?")

    print(f"Embedding dimensions: {len(result)}")

    print("\n--- Testing Groq LLM ---")

    llm = loader.load_llm()
    response = llm.invoke("Hello, how are you?")

    print(response.content)



# =============================================================================
# MODEL LOADER - PURPOSE & FLOW
# =============================================================================
#
# Purpose:
# Central place for API keys, embedding models, and LLM initialization.
#
#   .env (Local) / ECS (Production)
#                │
#                ▼
#          ApiKeyManager
#                │
#                ▼
# config.yaml ─► ModelLoader
#                │
#        ┌───────┴────────┐
#        ▼                ▼
# load_embeddings()   load_llm()
#        │                │
#   ┌────┴────┐      ┌────┴────┐
#   ▼         ▼      ▼         ▼
# Google     HF    Google     Groq
#   │         │      │         │
#   └────┬────┘      └────┬────┘
#        ▼                ▼
#   Embeddings            LLM
#        │                │
#        ▼                ▼
#      FAISS          RAG Answer
#
# =============================================================================