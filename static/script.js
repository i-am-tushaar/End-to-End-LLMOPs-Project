
const uploadForm = document.getElementById("upload-form");
const fileInput = document.getElementById("file-input");
const dropZone = document.getElementById("drop-zone");
const selectedFiles = document.getElementById("selected-files");
const uploadButton = document.getElementById("upload-button");
const uploadStatus = document.getElementById("upload-status");

const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const chatMessages = document.getElementById("chat-messages");
const chatSubtitle = document.getElementById("chat-subtitle");
const emptyState = document.getElementById("empty-state");

const sidebarStatus = document.getElementById("sidebar-status");
const sidebarStatusDot = document.getElementById("sidebar-status-dot");

let sessionId = null;
let isUploading = false;
let isSending = false;

function setStatus(element, message, type) {
    element.textContent = message;
    element.className = `status-message visible ${type}`;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function displaySelectedFiles() {
    selectedFiles.replaceChildren();

    Array.from(fileInput.files || []).forEach((file) => {
        const item = document.createElement("div");
        item.className = "file-item";

        const name = document.createElement("strong");
        name.textContent = file.name;

        const size = document.createElement("span");
        size.textContent = formatFileSize(file.size);

        item.append(name, size);
        selectedFiles.appendChild(item);
    });
}

function setSelectedFiles(files) {
    const transfer = new DataTransfer();

    Array.from(files).forEach((file) => transfer.items.add(file));
    fileInput.files = transfer.files;
    displaySelectedFiles();
}

fileInput.addEventListener("change", displaySelectedFiles);

// Drag-and-drop upload support
["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropZone.classList.add("drag-over");
    });
});

["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropZone.classList.remove("drag-over");
    });
});

dropZone.addEventListener("drop", (event) => {
    if (event.dataTransfer.files.length) {
        setSelectedFiles(event.dataTransfer.files);
    }
});

// Check whether the FastAPI backend is running
async function checkBackendHealth() {
    try {
        const response = await fetch("/health");

        if (!response.ok) {
            throw new Error("Backend health check failed");
        }

        const data = await response.json();

        if (data.status !== "ok") {
            throw new Error("Unexpected health status");
        }

        sidebarStatus.textContent = "Backend connected";
        sidebarStatusDot.className = "status-dot online";
    } catch (error) {
        sidebarStatus.textContent = "Backend unavailable";
        sidebarStatusDot.className = "status-dot offline";
        console.error("Health check failed:", error);
    }
}

async function readApiResponse(response) {
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        const detail = data.detail;
        const message = typeof detail === "string"
            ? detail
            : detail
                ? JSON.stringify(detail)
                : `Request failed (${response.status})`;

        throw new Error(message);
    }

    return data;
}

// Upload documents and create a searchable FAISS index
uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (isUploading) return;

    const files = Array.from(fileInput.files || []);

    if (files.length === 0) {
        setStatus(uploadStatus, "Please select at least one file.", "error");
        return;
    }

    isUploading = true;
    uploadButton.disabled = true;
    uploadButton.querySelector("span:first-child").textContent =
        "Uploading and indexing...";
    setStatus(uploadStatus, "Processing documents. Please wait...", "loading");

    try {
        const formData = new FormData();

        files.forEach((file) => formData.append("files", file));

        const response = await fetch("/upload", {
            method: "POST",
            body: formData
        });

        const data = await readApiResponse(response);

        if (!data.session_id || data.indexed !== true) {
            throw new Error("The server did not confirm successful indexing.");
        }

        sessionId = data.session_id;

        chatMessages.replaceChildren();
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.placeholder = "Ask something about your documents...";
        chatSubtitle.textContent = `${files.length} file(s) indexed and ready`;
        chatMessages.style.scrollBehavior = "smooth";

        addMessage(
            "assistant",
            `Your documents are ready! I indexed ${files.length} file(s). What would you like to know?`
        );

        setStatus(
            uploadStatus,
            data.message || "Documents indexed successfully.",
            "success"
        );

        fileInput.value = "";
        displaySelectedFiles();
    } catch (error) {
        setStatus(uploadStatus, error.message, "error");
        console.error("Document upload failed:", error);
    } finally {
        isUploading = false;
        uploadButton.disabled = false;
        uploadButton.querySelector("span:first-child").textContent =
            "Upload & Index Documents";
    }
});

// Add a safely rendered chat message
function addMessage(role, content) {
    emptyState?.remove();

    const message = document.createElement("div");
    message.className = `message ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = role === "user" ? "You" : "AI";
    avatar.setAttribute("aria-hidden", "true");

    const text = document.createElement("div");
    text.className = "message-content";
    text.textContent = content;

    message.append(avatar, text);
    chatMessages.appendChild(message);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return message;
}

// Send a question to the FastAPI /chat endpoint
chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (isSending) return;

    const message = messageInput.value.trim();

    if (!sessionId) {
        addMessage("assistant", "Please upload and index your documents first.");
        return;
    }

    if (!message) return;

    isSending = true;
    sendButton.disabled = true;
    messageInput.disabled = true;

    addMessage("user", message);
    messageInput.value = "";
    messageInput.style.height = "42px";

    const thinkingMessage = addMessage("assistant", "Thinking...");

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                session_id: sessionId,
                message: message
            })
        });

        const data = await readApiResponse(response);

        if (typeof data.answer !== "string") {
            throw new Error("The server returned an invalid answer.");
        }

        thinkingMessage.querySelector(".message-content").textContent =
            data.answer;
    } catch (error) {
        thinkingMessage.querySelector(".message-content").textContent =
            `Sorry, the request failed: ${error.message}`;

        console.error("Chat request failed:", error);
    } finally {
        isSending = false;
        sendButton.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});

// Enter sends; Shift + Enter creates a new line
messageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();

        if (!sendButton.disabled) {
            chatForm.requestSubmit();
        }
    }
});

// Automatically grow the message box
messageInput.addEventListener("input", () => {
    messageInput.style.height = "42px";
    messageInput.style.height =
        `${Math.min(messageInput.scrollHeight, 130)}px`;
});

checkBackendHealth();
