import pytest
from unittest.mock import MagicMock

import multi_doc_chat.utils.model_loader as model_module
from multi_doc_chat.exception.custom_exception import DocumentPortalException
from multi_doc_chat.utils.model_loader import ApiKeyManager, ModelLoader


# ## Test 1: Load API keys from environment variables
# Objective: Verify that ApiKeyManager loads Google and Groq API keys
# from environment variables.
def test_api_key_manager_loads_keys_from_environment(monkeypatch):

    monkeypatch.delenv("apikeyliveclass", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

    manager = ApiKeyManager()

    assert manager.get("GOOGLE_API_KEY") == "test-google-key"
    assert manager.get("GROQ_API_KEY") == "test-groq-key"


# ## Test 2: Handle missing API keys
# Objective: Verify that ApiKeyManager raises DocumentPortalException
# when the required API keys are unavailable.
def test_api_key_manager_raises_error_when_keys_missing(monkeypatch):

    monkeypatch.delenv("apikeyliveclass", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(
        DocumentPortalException,
        match="Missing API keys",
    ):
        ApiKeyManager()


# ## Test 3: Load API keys from ECS secrets
# Objective: Verify that ApiKeyManager extracts API keys from
# a valid JSON ECS secret stored in an environment variable.
def test_api_key_manager_loads_keys_from_ecs_secret(monkeypatch):

    monkeypatch.setenv(
        "apikeyliveclass",
        '{"GOOGLE_API_KEY": "ecs-google-key", '
        '"GROQ_API_KEY": "ecs-groq-key"}',
    )
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    manager = ApiKeyManager()

    assert manager.get("GOOGLE_API_KEY") == "ecs-google-key"
    assert manager.get("GROQ_API_KEY") == "ecs-groq-key"


# ## Test 4: Handle invalid ECS secrets
# Objective: Verify that invalid ECS JSON does not prevent API keys
# from being loaded from valid environment variables.
def test_api_key_manager_handles_invalid_ecs_secret(monkeypatch):

    monkeypatch.setenv("apikeyliveclass", "{invalid-json")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

    manager = ApiKeyManager()

    assert manager.get("GOOGLE_API_KEY") == "test-google-key"
    assert manager.get("GROQ_API_KEY") == "test-groq-key"


# ## Test 5: Request a missing API key
# Objective: Verify that requesting an API key that is not configured
# raises a KeyError with a meaningful error message.
def test_api_key_manager_get_missing_key(monkeypatch):

    monkeypatch.setenv(
        "apikeyliveclass",
        '{"GOOGLE_API_KEY": "test-google-key", '
        '"GROQ_API_KEY": "test-groq-key"}',
    )
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    manager = ApiKeyManager()

    with pytest.raises(
        KeyError,
        match="API key 'UNKNOWN_KEY' is missing",
    ):
        manager.get("UNKNOWN_KEY")


# ## Test 6: Load Google embeddings
# Objective: Verify that the Google embedding model is initialized
# with the configured model name and Google API key.
def test_load_google_embeddings_success(monkeypatch):

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
    mock_constructor = MagicMock(return_value=mock_embeddings)

    monkeypatch.setattr(
        model_module,
        "GoogleGenerativeAIEmbeddings",
        mock_constructor,
    )

    result = loader.load_embeddings()

    assert result is mock_embeddings
    mock_constructor.assert_called_once_with(
        model="test-embedding-model",
        google_api_key="test-google-key",
    )


# ## Test 7: Load Hugging Face embeddings
# Objective: Verify that the Hugging Face embedding model is initialized
# with the configured model name without requesting an API key.
def test_load_huggingface_embeddings_success(monkeypatch):

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


# ## Test 8: Handle unsupported embedding provider
# Objective: Verify that an unsupported embedding provider raises
# DocumentPortalException instead of loading an invalid provider.
def test_load_embeddings_unsupported_provider(monkeypatch):

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


# ## Test 9: Handle missing embedding provider configuration
# Objective: Verify that a provider selected through the environment
# but absent from the configuration raises DocumentPortalException.
def test_load_embeddings_missing_provider_config(monkeypatch):

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


# ## Test 10: Load Google Gemini LLM
# Objective: Verify that the Google Gemini LLM is initialized with
# the configured model name, API key, temperature, and output token limit.
def test_load_google_llm_success(monkeypatch):

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


# ## Test 11: Load Groq LLM
# Objective: Verify that the Groq LLM is initialized with the configured
# model name, API key, temperature, and maximum token count.
def test_load_groq_llm_success(monkeypatch):

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

    monkeypatch.setattr(
        model_module,
        "ChatGroq",
        mock_constructor,
    )

    result = loader.load_llm()

    assert result is mock_llm
    mock_constructor.assert_called_once_with(
        model="test-groq-model",
        api_key="test-groq-key",
        temperature=0.3,
        max_tokens=1024,
    )


# ## Test 12: Handle unsupported LLM provider
# Objective: Verify that an unsupported LLM provider raises
# DocumentPortalException instead of loading an invalid provider.
def test_load_llm_unsupported_provider(monkeypatch):

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


# ## Test 13: Handle missing LLM provider configuration
# Objective: Verify that selecting an LLM provider absent from the
# configuration raises DocumentPortalException.
def test_load_llm_missing_provider_config(monkeypatch):

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
