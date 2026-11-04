"""Local stand-in for the NVIDIA chat and rerank APIs, for browser tests.

It tests the application around the model, not model quality. Its answers are
scripted, so passing scenarios say nothing about real answers or abstention.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import threading

CALLS = {"chat": 0, "rerank": 0}
LOCK = threading.Lock()
STOP = {"a", "an", "the", "of", "to", "is", "do", "does", "its", "and", "when", "how", "who", "what", "must"}


def words(text):
    return {word for word in re.findall(r"[a-z0-9]+", text.lower()) if word not in STOP}


def answer_from_context(prompt):
    question = prompt.split("Current question:")[1].split("Instructions:")[0]
    context = prompt.split("Current question:")[0]

    if "salary" in question.lower():
        return "The documents do not contain this information."

    best = (0, None, None)

    for chunk_id, body in re.findall(r"\[Chunk ID: (\d+)\]\s*(.*?)(?=\[Chunk ID:|\Z)", context, re.S):
        for sentence in re.split(r"(?<=[.!?])\s+", body):
            overlap = len(words(sentence) & words(question))

            if overlap > best[0]:
                best = (overlap, sentence.strip(), chunk_id)

    if best[1] is None:
        return "The documents do not contain this information."

    return f"{best[1]} [Chunk ID: {best[2]}]"


def chat_reply(messages):
    system = messages[0]["content"]
    last = messages[-1]["content"]

    if "query rewriting" in system:
        return "When do Harbor Point fuel deliveries arrive?"

    if "GENERATED ANSWER" in last:
        if "mockungrounded" in last:
            return json.dumps({"grounded": False, "unsupported_claims": ["A mock claim."], "explanation": "mock"})

        return json.dumps({"grounded": True, "unsupported_claims": [], "explanation": "mock"})

    return answer_from_context(last)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def send(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.send(200, CALLS)

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        raw = json.dumps(request)
        kind = "chat" if "chat/completions" in self.path else "rerank"

        with LOCK:
            CALLS[kind] += 1

        if kind == "chat":
            if "mockfailgen" in raw:
                return self.send(500, {"error": "MOCK-PROVIDER-INTERNAL-DETAIL"})

            return self.send(200, {
                "id": "mock", "object": "chat.completion", "created": 0, "model": request["model"],
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": chat_reply(request["messages"])}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            })

        if "mockfailrerank" in raw:
            return self.send(500, {"error": "MOCK-PROVIDER-INTERNAL-DETAIL"})

        query = words(request["query"]["text"])
        scored = sorted(
            ((len(words(p["text"]) & query), i) for i, p in enumerate(request["passages"])),
            key=lambda pair: (-pair[0], pair[1]),
        )
        self.send(200, {"rankings": [{"index": i, "logit": float(score)} for score, i in scored]})


ThreadingHTTPServer(("0.0.0.0", 9000), Handler).serve_forever()
