
"""
Integration Test 4: API Upload and Chat

Tests the end-to-end workflow:
POST /upload -> create FAISS index -> POST /chat -> return answer.

Run:
    uv run pytest tests/integration/04_test_api_upload_chat.py -v
"""

from pathlib import Path

import main


def test_api_upload_then_chat(
    client,
    tmp_dirs,
    clear_sessions,
    stub_model_loader,
):
    # Step 1: Prepare a sample document with known information.
    content = (
        "Lakshya AI is an AI-powered learning platform. "
        "It helps students prepare for competitive examinations."
    )

    # Step 2: Upload the document through the actual FastAPI endpoint.
    # The multipart field name must match the API parameter: "files".
    upload_response = client.post(
        "/upload",
        files={
            "files": (
                "lakshya_guide.txt",
                content.encode("utf-8"),
                "text/plain",
            )
        },
    )

    # Step 3: Verify that the upload endpoint succeeds.
    assert upload_response.status_code == 200

    upload_data = upload_response.json()
    assert upload_data["indexed"] is True
    assert upload_data["session_id"]
    assert upload_data["message"]

    # Step 4: Get the actual session ID returned by the API.
    session_id = upload_data["session_id"]

    # Step 5: Verify that FAISS index files were created.
    index_dir = tmp_dirs["faiss"] / session_id

    assert (index_dir / "index.faiss").exists()
    assert (index_dir / "index.pkl").exists()

    # Step 6: Verify that the API initialized chat history.
    assert session_id in main.SESSIONS
    assert main.SESSIONS[session_id] == []

    # Step 7: Send a question through the actual chat endpoint.
    chat_response = client.post(
        "/chat",
        json={
            "session_id": session_id,
            "message": "What does Lakshya AI help students do?",
        },
    )

    # Step 8: Verify that the chat endpoint succeeds.
    assert chat_response.status_code == 200

    chat_data = chat_response.json()
    assert isinstance(chat_data["answer"], str)
    assert chat_data["answer"].strip()

    # Step 9: Verify that the conversation history was updated.
    history = main.SESSIONS[session_id]

    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
    assert history[0]["content"] == (
        "What does Lakshya AI help students do?"
    )
    assert history[1]["content"] == chat_data["answer"]


# ============================================================
# WORKFLOW OF THE INTEGRATION TEST
# ============================================================
# 1. Prepare a sample TXT document.
# 2. Send the document to the real FastAPI /upload endpoint.
# 3. ChatIngestor saves, loads, and splits the document.
# 4. Stub embeddings are used to create the FAISS index.
# 5. Verify that index.faiss and index.pkl are saved.
# 6. Retrieve the session ID returned by /upload.
# 7. Send a question to the real FastAPI /chat endpoint.
# 8. ConversationalRAG loads the saved FAISS index and builds
#    the LCEL chain using the stub LLM.
# 9. Verify the chat response and updated conversation history.
# 10. Use temporary directories so project data is not modified.
# ============================================================
