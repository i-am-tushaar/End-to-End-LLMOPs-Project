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
