"""HTTP API and demo page for the RAG assistant."""

from collections import defaultdict, deque
import os
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from guardrails import MAX_QUESTION_CHARS
from rag_chat import rag_chat


RATE_LIMIT_REQUESTS = int(os.getenv("RAG_RATE_LIMIT_REQUESTS", "10"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RAG_RATE_LIMIT_WINDOW_SECONDS", "60"))

app = FastAPI(title="Hybrid RAG Assistant")
_requests_by_client = defaultdict(deque)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)


class ChatResponse(BaseModel):
    answer: str


def enforce_rate_limit(client_id):
    now = time.monotonic()
    requests = _requests_by_client[client_id]

    while requests and now - requests[0] > RATE_LIMIT_WINDOW_SECONDS:
        requests.popleft()

    if len(requests) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(status_code=429, detail="Too many requests. Try again soon.")

    requests.append(now)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, request: Request):
    enforce_rate_limit(request.client.host if request.client else "unknown")

    try:
        return ChatResponse(answer=rag_chat(body.question))
    except Exception as error:
        # Details stay in the trace, so provider errors never reach visitors.
        raise HTTPException(
            status_code=503,
            detail="The assistant is unavailable right now.",
        ) from error


@app.get("/", response_class=HTMLResponse)
def home():
    return DEMO_PAGE


DEMO_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hybrid RAG Assistant</title>
<style>
body{font:16px/1.5 system-ui,sans-serif;max-width:720px;margin:0 auto;padding:32px 16px;color:#1f2933}
h1{font-size:24px;margin:0 0 4px}p{color:#52606d;margin:0 0 20px}
form{display:flex;gap:8px;flex-wrap:wrap}
input{flex:1 1 260px;padding:10px 12px;font:inherit;border:1px solid #9aa5b1;border-radius:6px}
button{padding:10px 18px;font:inherit;border:0;border-radius:6px;background:#1f3864;color:#fff;cursor:pointer}
button:disabled{opacity:.6;cursor:wait}
#answer{white-space:pre-wrap;margin-top:20px;padding:14px;background:#f5f7fa;border-radius:6px;min-height:24px}
</style></head><body>
<h1>Hybrid RAG Assistant</h1>
<p>Answers come from the indexed documents, with citations to their source chunks.</p>
<form id="f"><input id="q" maxlength="2000" required aria-label="Question"
placeholder="Ask about the indexed documents"><button id="b">Ask</button></form>
<div id="answer" role="status" aria-live="polite"></div>
<script>
const f=document.getElementById('f'),q=document.getElementById('q'),
b=document.getElementById('b'),a=document.getElementById('answer');
f.addEventListener('submit',async e=>{e.preventDefault();b.disabled=true;a.textContent='Searching...';
try{const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({question:q.value})});const d=await r.json();
a.textContent=r.ok?d.answer:(typeof d.detail==='string'?d.detail:'Please check your question.');}
catch{a.textContent='Could not reach the assistant.';}finally{b.disabled=false;}});
</script></body></html>"""
