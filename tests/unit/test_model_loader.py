import pytest

from multi_doc_chat.utils.model_loader import ApiKeyManager


def test_api_key_manager_loads_keys_from_environment(monkeypatch):
    """Test that API keys are loaded from environment variables."""

    monkeypatch.delenv("apikeyliveclass", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

    manager = ApiKeyManager()

    assert manager.get("GOOGLE_API_KEY") == "test-google-key"
    assert manager.get("GROQ_API_KEY") == "test-groq-key"

from multi_doc_chat.exception.custom_exception import DocumentPortalException



def test_api_key_manager_raises_error_when_keys_missing(monkeypatch):
    """Test that missing API keys raise an exception."""

    monkeypatch.delenv("apikeyliveclass", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(
        DocumentPortalException,
        match="Missing API keys"
    ):
        ApiKeyManager()



def test_api_key_manager_loads_keys_from_ecs_secret(monkeypatch):
    """Test that API keys are loaded from ECS JSON secrets."""

    monkeypatch.setenv(
        "apikeyliveclass",
        '{"GOOGLE_API_KEY": "ecs-google-key", '
        '"GROQ_API_KEY": "ecs-groq-key"}'
    )
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    manager = ApiKeyManager()

    assert manager.get("GOOGLE_API_KEY") == "ecs-google-key"
    assert manager.get("GROQ_API_KEY") == "ecs-groq-key"



def test_api_key_manager_handles_invalid_ecs_secret(monkeypatch):
    """Test fallback to environment variables when ECS JSON is invalid."""

    monkeypatch.setenv("apikeyliveclass", "{invalid-json")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

    manager = ApiKeyManager()

    assert manager.get("GOOGLE_API_KEY") == "test-google-key"
    assert manager.get("GROQ_API_KEY") == "test-groq-key"



def test_api_key_manager_get_missing_key(monkeypatch):
    """Test that requesting a missing API key raises KeyError."""

    monkeypatch.setenv(
        "apikeyliveclass",
        '{"GOOGLE_API_KEY": "test-google-key", '
        '"GROQ_API_KEY": "test-groq-key"}'
    )
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    manager = ApiKeyManager()

    with pytest.raises(KeyError, match="API key 'UNKNOWN_KEY' is missing"):
        manager.get("UNKNOWN_KEY")


from unittest.mock import MagicMock

import multi_doc_chat.utils.model_loader as model_module
from multi_doc_chat.utils.model_loader import ModelLoader


def test_load_google_embeddings_success(monkeypatch):
    """Test successful initialization of Google embeddings."""

    monkeypatch.setenv("EMBEDDING_PROVIDER", "google")

    loader = ModelLoader.__new__(ModelLoader)
    loader.config = {
        "embedding_model": {
            "google": {"model_name": "test-embedding-model"}
        }
    }
    loader.api_keys = MagicMock()
    loader.api_keys.get.return_value = "test-google-key"

    mock_embeddings = MagicMock()
    monkeypatch.setattr(
        model_module,
        "GoogleGenerativeAIEmbeddings",
        MagicMock(return_value=mock_embeddings),
    )

    result = loader.load_embeddings()

    assert result is mock_embeddings
    model_module.GoogleGenerativeAIEmbeddings.assert_called_once_with(
        model="test-embedding-model",
        google_api_key="test-google-key",
    )



def test_load_huggingface_embeddings_success(monkeypatch):
    """Test successful initialization of Hugging Face embeddings."""

    monkeypatch.setenv("EMBEDDING_PROVIDER", "huggingface")

    loader = ModelLoader.__new__(ModelLoader)
    loader.config = {
        "embedding_model": {
            "huggingface": {
                "model_name": "test-huggingface-model"
            }
        }
    }
    loader.api_keys = MagicMock()

    mock_embeddings = MagicMock()
    mock_constructor = MagicMock(return_value=mock_embeddings)

    monkeypatch.setattr(
        model_module,
        "HuggingFaceEmbeddings",
        mock_constructor,
    )

    result = loader.load_embeddings()

    assert result is mock_embeddings
    mock_constructor.assert_called_once_with(
        model_name="test-huggingface-model"
    )
    loader.api_keys.get.assert_not_called()



def test_load_embeddings_unsupported_provider(monkeypatch):
    """Test that an unsupported embedding provider raises an exception."""

    monkeypatch.setenv("EMBEDDING_PROVIDER", "unsupported")

    loader = ModelLoader.__new__(ModelLoader)
    loader.config = {
        "embedding_model": {
            "unsupported": {"model_name": "test-model"}
        }
    }
    loader.api_keys = MagicMock()

    with pytest.raises(
        DocumentPortalException,
        match="Failed to load embeddings",
    ):
        loader.load_embeddings()




def test_load_embeddings_missing_provider_config(monkeypatch):
    """Test that a missing embedding provider configuration raises an exception."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "missing")

    loader = ModelLoader.__new__(ModelLoader)
    loader.config = {
        "embedding_model": {
            "google": {"model_name": "test-embedding-model"}
        }
    }
    loader.api_keys = MagicMock()

    with pytest.raises(
        DocumentPortalException,
        match="Failed to load embeddings",
    ):
        loader.load_embeddings()



def test_load_google_llm_success(monkeypatch):
    """Test successful initialization of Google Gemini LLM."""
    monkeypatch.setenv("LLM_PROVIDER", "google")

    loader = ModelLoader.__new__(ModelLoader)
    loader.config = {
        "llm": {
            "google": {
                "model_name": "test-gemini-model",
                "temperature": 0.2,
                "max_output_tokens": 1024,
            }
        }
    }
    loader.api_keys = MagicMock()
    loader.api_keys.get.return_value = "test-google-key"

    mock_llm = MagicMock()
    mock_constructor = MagicMock(return_value=mock_llm)
    monkeypatch.setattr(
        model_module,
        "ChatGoogleGenerativeAI",
        mock_constructor,
    )

    result = loader.load_llm()

    assert result is mock_llm
    mock_constructor.assert_called_once_with(
        model="test-gemini-model",
        google_api_key="test-google-key",
        temperature=0.2,
        max_output_tokens=1024,
    )



def test_load_groq_llm_success(monkeypatch):
    """Test successful initialization of Groq LLM."""
    monkeypatch.setenv("LLM_PROVIDER", "groq")

    loader = ModelLoader.__new__(ModelLoader)
    loader.config = {
        "llm": {
            "groq": {
                "model_name": "test-groq-model",
                "temperature": 0.3,
                "max_output_tokens": 1024,
            }
        }
    }
    loader.api_keys = MagicMock()
    loader.api_keys.get.return_value = "test-groq-key"

    mock_llm = MagicMock()
    mock_constructor = MagicMock(return_value=mock_llm)
    monkeypatch.setattr(model_module, "ChatGroq", mock_constructor)

    result = loader.load_llm()

    assert result is mock_llm
    mock_constructor.assert_called_once_with(
        model="test-groq-model",
        api_key="test-groq-key",
        temperature=0.3,
        max_tokens=1024,
    )




def test_load_llm_unsupported_provider(monkeypatch):
    """Test that an unsupported LLM provider raises an exception."""
    monkeypatch.setenv("LLM_PROVIDER", "unsupported")

    loader = ModelLoader.__new__(ModelLoader)
    loader.config = {
        "llm": {
            "unsupported": {"model_name": "test-model"}
        }
    }
    loader.api_keys = MagicMock()

    with pytest.raises(
        DocumentPortalException,
        match="Failed to load LLM",
    ):
        loader.load_llm()




def test_load_llm_missing_provider_config(monkeypatch):
    """Test that missing LLM provider configuration raises an exception."""
    monkeypatch.setenv("LLM_PROVIDER", "missing")

    loader = ModelLoader.__new__(ModelLoader)
    loader.config = {
        "llm": {
            "google": {"model_name": "test-gemini-model"}
        }
    }
    loader.api_keys = MagicMock()

    with pytest.raises(
        DocumentPortalException,
        match="Failed to load LLM",
    ):
        loader.load_llm()
