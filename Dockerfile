
# 1. Use official Python 3.11 slim image
FROM python:3.11-slim

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PYTHONPATH="/app:/app/multi_doc_chat" \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 3. Set working directory
WORKDIR /app

# 4. Install required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 5. Copy uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 6. Copy production dependency file
COPY requirements.txt ./

# 7. Install CPU-only PyTorch
RUN uv pip install --system \
    --index-url https://download.pytorch.org/whl/cpu \
    torch

# 8. Install remaining application dependencies
RUN uv pip install --system --no-cache -r requirements.txt

# 9. Copy application source code
COPY . .

# 10. Expose FastAPI application port
EXPOSE 8080

# 11. Start FastAPI application using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
