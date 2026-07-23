FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# pre-warm Chroma embedding model cache so it doesn't download at runtime
RUN python -c "import chromadb; chromadb.PersistentClient(path='/tmp/chroma_warm').get_or_create_collection('warm')"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
