FROM python:3.12-slim

WORKDIR /app

# System deps: Tesseract (OCR) + curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-kor \
    tesseract-ocr-eng \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install rhwp CLI (HWP parser) from source
ARG RHWP_VERSION=v0.7.7
RUN apt-get update && apt-get install -y --no-install-recommends cargo rustc \
    && git clone --depth 1 --branch ${RHWP_VERSION} https://github.com/edwardkim/rhwp.git /tmp/rhwp \
    && cd /tmp/rhwp && cargo build --release \
    && cp /tmp/rhwp/target/release/rhwp /usr/local/bin/rhwp \
    && rm -rf /tmp/rhwp \
    && apt-get remove -y cargo rustc && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
