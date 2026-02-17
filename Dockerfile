# ============================================================
# Eco Pharm Telegram Bot - Production Dockerfile
# Linux Server uchun optimallashtirilgan - 24/7 ishlash
# ============================================================

FROM python:3.11-slim-bookworm

# Build argumentlari
ARG BUILD_DATE
ARG VERSION=1.0.0

# Labellar
LABEL maintainer="Eco Pharm Team"
LABEL version="${VERSION}"
LABEL build-date="${BUILD_DATE}"
LABEL description="Eco Pharm Telegram Bot - 24/7 production ready"

# Environment sozlamalari
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Tashkent \
    APP_HOME=/app \
    APP_USER=botuser \
    APP_UID=1000 \
    APP_GID=1000

# Working directory
WORKDIR ${APP_HOME}

# System dependencies va timezone sozlash
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tzdata \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo ${TZ} > /etc/timezone \
    && dpkg-reconfigure -f noninteractive tzdata

# Non-root user yaratish
RUN groupadd -g ${APP_GID} ${APP_USER} \
    && useradd -m -u ${APP_UID} -g ${APP_GID} -s /bin/bash ${APP_USER}

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Application code nusxalash
COPY --chown=${APP_USER}:${APP_USER} config.py main.py bot.py states.py ./

# Directories
COPY --chown=${APP_USER}:${APP_USER} handlers/ ./handlers/
COPY --chown=${APP_USER}:${APP_USER} keyboards/ ./keyboards/
COPY --chown=${APP_USER}:${APP_USER} database/ ./database/
COPY --chown=${APP_USER}:${APP_USER} utils/ ./utils/
COPY --chown=${APP_USER}:${APP_USER} middlewares/ ./middlewares/

# Data va log papkalarini yaratish
RUN mkdir -p ${APP_HOME}/data ${APP_HOME}/logs \
    && chown -R ${APP_USER}:${APP_USER} ${APP_HOME} \
    && chmod -R 755 ${APP_HOME} \
    && chmod 777 ${APP_HOME}/data \
    && chmod 777 ${APP_HOME}/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import asyncio; from database.db_postgres import engine; asyncio.run(engine.dispose())" || exit 1

# Non-root user ga o'tish
USER ${APP_USER}

# Tini entrypoint sifatida (zombie processes oldini olish)
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run bot
CMD ["python", "-u", "main.py"]