"""Centralized loader for API keys, embeddings, and chat models."""

import json
import os
import sys

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq

try:
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
except ImportError:  # Google support is optional unless selected.
    ChatGoogleGenerativeAI = None
    GoogleGenerativeAIEmbeddings = None

from multi_doc_chat.utils.config_loader import load_config
from multi_doc_chat.logger import GLOBAL_LOGGER as log
from multi_doc_chat.exception.custom_exception import DocumentPortalException


class ApiKeyManager:
    """Load API keys from direct environment variables or an ECS JSON secret."""

    SUPPORTED_KEYS = ("GOOGLE_API_KEY", "GROQ_API_KEY")

    def __init__(self):
        self.api_keys = {}

        # ECS can inject a JSON secret through this environment variable.
        raw_secret = os.getenv("apikeyliveclass")
        if raw_secret:
            try:
                secret_values = json.loads(raw_secret)
                if isinstance(secret_values, dict):
                    for key in self.SUPPORTED_KEYS:
                        value = secret_values.get(key)
                        if value:
                            self.api_keys[key] = value
                else:
                    log.warning("ECS API secret must contain a JSON object")
            except (json.JSONDecodeError, TypeError):
                log.warning("Could not parse apikeyliveclass JSON secret")

        # Direct environment variables take precedence over JSON values.
        for key in self.SUPPORTED_KEYS:
            value = os.getenv(key)
            if value:
                self.api_keys[key] = value

        if not any(self.api_keys.values()):
            raise DocumentPortalException("Missing API keys: configure GOOGLE_API_KEY or GROQ_API_KEY", sys)

        log.info("API key manager initialized")

    def get(self, key: str) -> str:
        """Return an API key or raise KeyError when it is unavailable."""
        value = self.api_keys.get(key) or os.getenv(key)
        if not value:
            raise KeyError(f"API key '{key}' is missing")
        return value


class ModelLoader:
    """Load the configured embedding provider and LLM provider."""

    def __init__(self):
        # Do not overwrite provider selections supplied by the environment.
        if os.getenv("APP_ENV", "development").lower() != "production":
            load_dotenv(override=False)
            log.info("Running in LOCAL mode")
        else:
            log.info("Running in PRODUCTION mode")

        self.config = load_config()
        self.api_keys = ApiKeyManager()

        embedding_defaults = self.config.get("embedding_model", {})
        llm_defaults = self.config.get("llm", {})

        configured_embedding_provider = next((name for name, settings in embedding_defaults.items() if isinstance(settings, dict) and settings.get("provider") == name), "huggingface")
        configured_llm_provider = next((name for name, settings in llm_defaults.items() if isinstance(settings, dict) and settings.get("provider") == name), "groq")

        self.embedding_provider = os.getenv("EMBEDDING_PROVIDER", configured_embedding_provider).strip().lower()
        self.llm_provider = os.getenv("LLM_PROVIDER", configured_llm_provider).strip().lower()

        log.info("Selected providers", embedding_provider=self.embedding_provider, llm_provider=self.llm_provider)

        # Validate only the key required by the selected LLM.
        if self.llm_provider == "google":
            self.api_keys.get("GOOGLE_API_KEY")
        elif self.llm_provider == "groq":
            self.api_keys.get("GROQ_API_KEY")

    def load_embeddings(self):
        """Initialize Google or Hugging Face embeddings."""
        try:
            provider = getattr(self, "embedding_provider", os.getenv("EMBEDDING_PROVIDER", next((name for name, settings in self.config.get("embedding_model", {}).items() if isinstance(settings, dict) and settings.get("provider") == name), "huggingface"))).strip().lower()
            cfg = self.config["embedding_model"][provider]
            model = cfg["model_name"]

            if provider == "huggingface":
                log.info("Loading embeddings", provider=provider, model=model)
                return HuggingFaceEmbeddings(model_name=model)

            if provider == "google":
                if GoogleGenerativeAIEmbeddings is None:
                    raise ImportError("Install langchain-google-genai to use Google embeddings")
                return GoogleGenerativeAIEmbeddings(model=model, google_api_key=self.api_keys.get("GOOGLE_API_KEY"))

            raise ValueError(f"Unsupported embedding provider: {provider}")

        except Exception as e:
            log.error("Failed to load embeddings", error=str(e))
            raise DocumentPortalException("Failed to load embeddings", sys) from e

    def load_llm(self):
        """Initialize Google Gemini or Groq chat model."""
        try:
            provider = getattr(self, "llm_provider", os.getenv("LLM_PROVIDER", next((name for name, settings in self.config.get("llm", {}).items() if isinstance(settings, dict) and settings.get("provider") == name), "groq"))).strip().lower()
            cfg = self.config["llm"][provider]

            model = cfg["model_name"]
            temperature = cfg.get("temperature", 0)
            max_tokens = cfg.get("max_output_tokens", 2048)

            log.info("Loading LLM", provider=provider, model=model)

            if provider == "groq":
                return ChatGroq(model=model, api_key=self.api_keys.get("GROQ_API_KEY"), temperature=temperature, max_tokens=max_tokens)

            if provider == "google":
                if ChatGoogleGenerativeAI is None:
                    raise ImportError("Install langchain-google-genai to use Google Gemini")
                return ChatGoogleGenerativeAI(model=model, google_api_key=self.api_keys.get("GOOGLE_API_KEY"), temperature=temperature, max_output_tokens=max_tokens)

            raise ValueError(f"Unsupported LLM provider: {provider}")

        except Exception as e:
            log.error("Failed to load LLM", error=str(e))
            raise DocumentPortalException("Failed to load LLM", sys) from e


if __name__ == "__main__":
    loader = ModelLoader()

    embeddings = loader.load_embeddings()
    print(f"Embedding dimensions: {len(embeddings.embed_query('Hello'))}")

    llm = loader.load_llm()
    print(llm.invoke("Hello, how are you?").content)


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