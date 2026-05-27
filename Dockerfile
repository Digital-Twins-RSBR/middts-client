# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements/base.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /tmp/requirements.txt

COPY . .
# Auto-create settings.py from settings_base if not present (e.g. in clean clones)
RUN [ ! -f client/settings.py ] && printf 'from .settings_base import *\n' > client/settings.py || true

EXPOSE 8002