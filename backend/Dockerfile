FROM python:3.11-slim

WORKDIR /app

# PYTHONDONTWRITEBYTECODE Prevents Python from writing .pyc files to disk. avoids __pycache__ directories.
# PYTHONUNBUFFERED Ensures Python outputs logs in real-time. flush stdin and stdout without buffering, which is useful for debugging and logging in Docker containers.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
