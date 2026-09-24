# Production Dockerfile for Mai AI
# Multi-stage build: builder stage + runtime stage
# Layer ordering: system deps -> Python deps -> app code (maximizes build cache)

# ---- Stage 1: Builder ----
FROM python:3.10-slim AS builder

# Install build dependencies (compilers for native Python extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Copy requirements first — maximizes Docker layer cache
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Copy application code
COPY . .

# ---- Stage 2: Runtime ----
FROM python:3.10-slim

# Install only runtime system dependencies (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN addgroup --system --gid 1001 mai && \
    adduser --system --uid 1001 --no-create-home --ingroup mai mai

# Copy virtual environment from builder
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"

# Copy application code from builder
COPY --from=builder /app /app

WORKDIR /app

# Switch to non-root user
USER mai

# Health check — verifies application is actually responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose application port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
