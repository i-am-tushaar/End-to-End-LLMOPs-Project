
"""
Integration Test 5: Config and Model Loading

Purpose:
    Verify that the real config.yaml loads correctly and that ModelLoader
    creates the configured embedding and LLM objects.

What is tested for real:
    - load_config() and YAML parsing
    - ModelLoader initialization
    - Provider selection and configuration lookup
    - Passing configuration and API keys to model constructors

What is replaced:
    - API key manager, to avoid depending on real credentials
    - Google embedding and LLM constructors, to avoid network calls
"""

from unittest.mock import Mock

import multi_doc_chat.utils.model_loader as model_loader_module
from multi_doc_chat.utils.config_loader import load_config


def test_config_and_model_loading(monkeypatch):
    """Verify real config loading and model initialization."""

    # Step 1: Load the real project configuration.
    config = load_config()

    assert isinstance(config, dict)
    assert "embedding_model" in config
    assert "llm" in config

    # Step 2: Confirm the Google provider configurations exist.
    assert "google" in config["embedding_model"]
    assert "google" in config["llm"]

    embedding_config = config["embedding_model"]["google"]
    llm_config = config["llm"]["google"]

    assert embedding_config["model_name"]
    assert llm_config["model_name"]

    # Step 3: Select Google providers for this test.
    monkeypatch.setenv("EMBEDDING_PROVIDER", "google")
    monkeypatch.setenv("LLM_PROVIDER", "google")

    # Step 4: Replace the API key manager with a safe test double.
    fake_api_keys = Mock()
    fake_api_keys.get.side_effect = {
        "GOOGLE_API_KEY": "test-google-key",
        "GROQ_API_KEY": "test-groq-key",
    }.get

    monkeypatch.setattr(
        model_loader_module,
        "ApiKeyManager",
        lambda: fake_api_keys,
    )

    # Step 5: Replace external model constructors.
    fake_embeddings = Mock(name="fake_embeddings")
    fake_llm = Mock(name="fake_llm")

    embedding_constructor = Mock(return_value=fake_embeddings)
    llm_constructor = Mock(return_value=fake_llm)

    monkeypatch.setattr(
        model_loader_module,
        "GoogleGenerativeAIEmbeddings",
        embedding_constructor,
    )
    monkeypatch.setattr(
        model_loader_module,
        "ChatGoogleGenerativeAI",
        llm_constructor,
    )

    # Step 6: Initialize the real ModelLoader.
    loader = model_loader_module.ModelLoader()

    # Step 7: Create embedding and LLM objects using the real loader methods.
    embeddings = loader.load_embeddings()
    llm = loader.load_llm()

    # Step 8: Verify the expected objects were returned.
    assert embeddings is fake_embeddings
    assert llm is fake_llm

    # Step 9: Verify the configured models and test API key were passed.
    embedding_constructor.assert_called_once_with(
        model=embedding_config["model_name"],
        google_api_key="test-google-key",
    )

    expected_llm_kwargs = {
        "model": llm_config["model_name"],
        "google_api_key": "test-google-key",
        "temperature": llm_config.get("temperature", 0),
        "max_output_tokens": llm_config.get("max_output_tokens", 2048),
    }

    llm_constructor.assert_called_once_with(**expected_llm_kwargs)



# =============================================================================
# WORKFLOW
# =============================================================================
#
# 1. load_config() reads the real config.yaml file.
# 2. The test verifies that embedding_model and llm configurations exist.
# 3. Environment variables select the Google embedding and LLM providers.
# 4. A fake ApiKeyManager supplies test API keys without using real credentials.
# 5. Google embedding and LLM constructors are mocked to prevent external API calls.
# 6. The real ModelLoader initializes and reads the configuration.
# 7. load_embeddings() creates the mocked embedding object using the configured model.
# 8. load_llm() creates the mocked LLM object using the configured model settings.
# 9. Assertions verify that the correct model names, API keys, and parameters are passed.
#
# Flow:
#
# config.yaml
#     |
#     v
# load_config()
#     |
#     v
# ModelLoader initialization
#     |
#     +---------------------------+
#     |                           |
#     v                           v
# load_embeddings()           load_llm()
#     |                           |
#     v                           v
# Google embeddings mock       Google LLM mock
#     |                           |
#     +-------------+-------------+
#                   |
#                   v
#       Verify objects and arguments
#                   |
#                   v
#              Test passes
#
# Run this test:
# uv run pytest tests/integration/05_test_config_model.py -v
#
# Run all integration tests:
# uv run pytest tests/integration/ -v
#
# =============================================================================
