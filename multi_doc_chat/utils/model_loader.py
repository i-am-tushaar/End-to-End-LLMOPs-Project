"""
Centralized loader for API keys, embedding models, and LLMs.
Supports Google/Hugging Face embeddings and Google/Groq LLMs.
"""

import os
import sys
import json

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq

from multi_doc_chat.utils.config_loader import load_config
from multi_doc_chat.logger import GLOBAL_LOGGER as log
from multi_doc_chat.exception.custom_exception import DocumentPortalException


class ApiKeyManager:
    """Loads and validates API keys from ECS secrets or environment variables."""

    REQUIRED_KEYS = ["GOOGLE_API_KEY", "GROQ_API_KEY"]

    def __init__(self):
        self.api_keys = self._load_ecs_secret()

        # ECS has priority; .env/environment fills missing keys.
        for key in self.REQUIRED_KEYS:
            if not self.api_keys.get(key) and os.getenv(key):
                self.api_keys[key] = os.getenv(key)

        missing = [k for k in self.REQUIRED_KEYS if not self.api_keys.get(k)]
        if missing:
            raise DocumentPortalException(f"Missing API keys: {', '.join(missing)}", sys)

        log.info("API keys loaded", keys=list(self.api_keys.keys()))

    def _load_ecs_secret(self) -> dict:
        """Load API keys from AWS ECS JSON secret."""
        raw = os.getenv("apikeyliveclass")
        if not raw:
            return {}

        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except Exception as e:
            log.warning("Failed to parse ECS secret", error=str(e))
            return {}

    def get(self, key: str) -> str:
        """Return an API key by name."""
        value = self.api_keys.get(key)
        if not value:
            raise KeyError(f"API key '{key}' is missing")
        return value


class ModelLoader:
    """Loads embedding models and LLMs based on config.yaml."""

    def __init__(self):
        # Load .env locally; production uses environment/ECS secrets.
        if os.getenv("ENV", "local").lower() != "production":
            load_dotenv()
            log.info("Running in LOCAL mode")

        self.api_keys = ApiKeyManager()
        self.config = load_config()

    def load_embeddings(self):
        """Load Google or Hugging Face embeddings."""
        try:
            provider = os.getenv("EMBEDDING_PROVIDER", "google").lower()
            cfg = self.config["embedding_model"].get(provider)

            if not cfg:
                raise ValueError(f"Embedding provider '{provider}' not found in config")

            model = cfg["model_name"]
            log.info("Loading embeddings", provider=provider, model=model)

            if provider == "google":
                return GoogleGenerativeAIEmbeddings(
                    model=model,
                    google_api_key=self.api_keys.get("GOOGLE_API_KEY"),
                )

            if provider == "huggingface":
                return HuggingFaceEmbeddings(model_name=model)

            raise ValueError(f"Unsupported embedding provider: {provider}")

        except Exception as e:
            log.error("Failed to load embeddings", error=str(e))
            raise DocumentPortalException("Failed to load embeddings", sys) from e

    def load_llm(self):
        """Load Google or Groq LLM."""
        try:
            provider = os.getenv("LLM_PROVIDER", "google").lower()
            cfg = self.config["llm"].get(provider)

            if not cfg:
                raise ValueError(f"LLM provider '{provider}' not found in config")

            model = cfg["model_name"]
            temperature = cfg.get("temperature", 0)
            max_tokens = cfg.get("max_output_tokens", 2048)

            log.info("Loading LLM", provider=provider, model=model)

            if provider == "google":
                return ChatGoogleGenerativeAI(
                    model=model,
                    google_api_key=self.api_keys.get("GOOGLE_API_KEY"),
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )

            if provider == "groq":
                return ChatGroq(
                    model=model,
                    api_key=self.api_keys.get("GROQ_API_KEY"),
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

            raise ValueError(f"Unsupported LLM provider: {provider}")

        except Exception as e:
            log.error("Failed to load LLM", error=str(e))
            raise DocumentPortalException("Failed to load LLM", sys) from e


if __name__ == "__main__":
    # Quick manual check: load and call both models directly
    loader = ModelLoader()

    # Test the embedding model
    embeddings = loader.load_embeddings()
    print(embeddings.embed_query("Hello, how are you?"))

    # Test the LLM
    llm = loader.load_llm()
    print(llm.invoke("Hello, how are you?").content))


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