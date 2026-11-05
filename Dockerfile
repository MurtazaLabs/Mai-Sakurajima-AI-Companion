FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch wheels before the application requirements.
# The default PyPI wheels can pull large NVIDIA CUDA runtimes, which are
# unnecessary for this CPU container and exhaust disk during ARM64 builds.
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

COPY . .

ENV MAI_OBSIDIAN_VAULT=/app/data/vault
ENV LOG_LEVEL=INFO

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]