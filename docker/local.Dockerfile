FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY config /app/config

RUN pip install --upgrade pip && pip install .

CMD ["python", "-m", "watcher.mock"]
