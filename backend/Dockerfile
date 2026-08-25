FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/root/.local/bin:/usr/local/bin:${PATH}"

WORKDIR /app

COPY scripts/bootstrap_tools.sh /usr/local/bin/bootstrap_tools.sh
RUN chmod 0755 /usr/local/bin/bootstrap_tools.sh \
    && BOOTSTRAP_UPDATE_CLAMAV=false \
       BOOTSTRAP_YARA_RULES=false \
       BOOTSTRAP_INSTALL_OPTIONAL=true \
       /usr/local/bin/bootstrap_tools.sh

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       curl \
       gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg \
       -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
       > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

RUN pip install checkov

RUN curl -fsSL \
    https://github.com/hadolint/hadolint/releases/latest/download/hadolint-Linux-x86_64 \
    -o /usr/local/bin/hadolint \
    && chmod +x /usr/local/bin/hadolint

COPY backend/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY backend /app
COPY backend/docker-entrypoint.sh /docker-entrypoint.sh

RUN DJANGO_SECRET_KEY=build-time-only python manage.py collectstatic --noinput

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/var/scans /app/var/uploads /app/var/yara_rules /app/var/file_sandbox /app/var/tool_locks /app/var/logs /var/lib/clamav \
    && chown -R appuser:appuser /app /docker-entrypoint.sh /var/lib/clamav \
    && chmod 0755 /docker-entrypoint.sh

USER appuser

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
