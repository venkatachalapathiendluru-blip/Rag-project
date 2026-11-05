FROM python:3.10-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 HF_HOME=/models RAG_UPLOAD_DIR=/app/uploads RAG_TRACE_DIR=/app/traces

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "from sentence_transformers import SentenceTransformer as S; S('all-MiniLM-L6-v2')"

COPY chunking.py guardrails.py tracing.py trace_report.py rag.py rag_chat.py hybrid_retriever.py ./
COPY backend ./backend
RUN useradd --create-home appuser && mkdir -p /app/traces /app/uploads && chown -R appuser /app /models
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/v1/health/')"
# One worker: ingestion jobs run in this process, and startup recovery assumes that.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
