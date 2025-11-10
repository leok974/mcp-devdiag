FROM python:3.13-slim

# playwright (optional) system deps; comment if not needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget ca-certificates fonts-liberation libnss3 libatk-bridge2.0-0 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libasound2 libatspi2.0-0 libgtk-3-0 libgbm1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./main.py

ENV PORT=8080
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
