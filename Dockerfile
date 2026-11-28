
# 1. Use Python 3.14
FROM python:3.14-slim

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PYTHONPATH="/app:/app/multi_doc_chat" \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 3. Set working directory
WORKDIR /app

# 4. Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 5. Install UV
COPY --from=ghcr.io/astral-sh/uv:0.11.23 /uv /uvx /bin/

# 6. Copy dependency files
COPY pyproject.toml uv.lock ./

# 7. Install production dependencies only
RUN uv sync --locked --no-dev --no-install-project

# 8. Copy application source code
COPY . .

# 9. Expose application port
EXPOSE 8080

# 10. Start FastAPI application
CMD ["uv", "run", "--no-sync", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
