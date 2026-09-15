# Stage 1: Frontend build
# The static bundle is architecture-independent. Build it once on the native
# runner instead of running Node and Vite again through ARM64 QEMU.
FROM --platform=$BUILDPLATFORM node:22-alpine AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit
COPY frontend/ ./
COPY TERMS.nl.md /build/TERMS.nl.md
RUN npm run build

# Stage 2: Python backend
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gosu \
    libgomp1 \
    libstdc++6 \
    tesseract-ocr \
    tesseract-ocr-nld \
    tesseract-ocr-eng \
    tesseract-ocr-deu \
    tesseract-ocr-fra \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 -s /bin/bash emcargo

WORKDIR /app

COPY backend/requirements-runtime-lock.txt ./requirements-runtime-lock.txt
RUN pip install --require-hashes -r requirements-runtime-lock.txt && pip check

COPY backend/ ./backend/
RUN rm -rf ./backend/tests ./backend/requirements.txt
COPY templates/ ./templates/
# The changelog the what's-new card serves after an update. Next to /app/backend
# so app/services/changelog.py finds it where a checkout keeps it: one level up.
COPY CHANGELOG.md ./CHANGELOG.md
COPY TERMS.nl.md LICENSE ./
COPY THIRD_PARTY_NOTICES.md TRADEMARKS.md ./
COPY licenses/ ./licenses/
# The UN cards are deliberately NOT in the image any more. The set (thousands
# of generated PDFs) is published as a GitHub Release by the "Generate UN
# cards" workflow and imported by an administrator into <data-dir>/un-cards/,
# where it survives restarts and updates. That took ~575 MB out of the image.

COPY --from=frontend-build /build/frontend/dist ./backend/static/

RUN chmod +x /app/backend/entrypoint.sh && chown -R emcargo:emcargo /app

WORKDIR /app/backend

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8080/api/health || exit 1

ENTRYPOINT ["/app/backend/entrypoint.sh"]
