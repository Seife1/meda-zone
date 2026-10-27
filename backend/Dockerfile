FROM python:3.11-slim

# System deps:
#   gcc + libpq-dev  — compile asyncpg / psycopg2 C extensions
#   libgeos-dev      — GeoAlchemy2 / Shapely geometry operations
#   ca-certificates  — outbound HTTPS to Firebase, Chapa, ArifPay
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libgeos-dev \
    ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies before copying source code so Docker can
# cache this layer and skip re-installing when only source files change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
