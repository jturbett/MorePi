FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn openai
COPY web_chatgpt.py .
EXPOSE 8080
CMD ["uvicorn", "web_chatgpt:app", "--host", "0.0.0.0", "--port", "8080"]

