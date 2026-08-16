# syntax=docker/dockerfile:1
# Image "slim" : base Debian 12 (bookworm) réduite. Sert de point de comparaison
# à l'image durcie « distroless » (Exp.3 : durcissement d'image).

# --- Étage build : dépendances runtime installées dans un préfixe isolé ---------
FROM python:3.11-slim-bookworm AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Étage runtime : slim + utilisateur non-root -------------------------------
FROM python:3.11-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY --from=builder /install /usr/local
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app
COPY app/ ./app/
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
