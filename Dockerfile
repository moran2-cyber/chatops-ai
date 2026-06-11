# Stage 1: Builder
FROM python:3.13-slim AS builder

WORKDIR /app

#install dependecies dulu
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.13-slim AS Runtime

# Non-root user untuk keamanan 
RUN useradd --create-home --shell /bin/bash chatops
WORKDIR /app

# Salin dependecies yang sudah di install ke runtime
COPY --from=builder /install /usr/local

# Salin kode aplikasi
COPY --chown=chatops:chatops . .

# Pakai user non-root
USER chatops

# Tidak ada port yang di expose-bot pakai Socket Mode (Outbound only)
CMD ["python", "main.py"]