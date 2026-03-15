# Build from repo root: docker build -t answer-agent -f services/answer_agent/Dockerfile .
FROM python:3.11-slim
WORKDIR /app
COPY services/shared /app/shared
COPY services/answer_agent/requirements.txt services/answer_agent/main.py ./
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
