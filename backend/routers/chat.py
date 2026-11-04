"""Chat turns and saved conversations."""

from fastapi import APIRouter, Depends, Request, Response

from backend import chat_service, repositories
from backend.db import connection
from backend.schemas import ChatRequest, ChatResponse, Conversation, ConversationSummary
from backend.security import chat_limiter, client_id, require_token


router = APIRouter(tags=["chat"], dependencies=[Depends(require_token)])


@router.post("/chat/", response_model=ChatResponse)
def chat(body: ChatRequest, request: Request):
    chat_limiter.check(client_id(request))
    return chat_service.answer_question(
        body.question, body.conversation_id, body.profile_id, body.document_ids
    )


@router.get("/conversations/", response_model=list[ConversationSummary])
def list_conversations():
    with connection() as conn:
        return repositories.list_conversations(conn)


@router.get("/conversations/{conversation_id}", response_model=Conversation)
def get_conversation(conversation_id: int):
    with connection() as conn:
        return repositories.get_conversation(conn, conversation_id)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int):
    with connection() as conn:
        repositories.delete_conversation(conn, conversation_id)

    return Response(status_code=204)
