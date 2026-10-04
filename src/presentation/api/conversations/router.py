import json
import os
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from application.conversations.command_handlers import (
    CreateConversationCommandHandler,
    SendUserMessageCommandHandler,
)
from application.conversations.commands import CreateConversationCommand, SendUserMessageCommand
from application.conversations.queries import GetConversationMessagesQuery, ListConversationsQuery
from application.conversations.query_handlers import (
    GetConversationMessagesQueryHandler,
    ListConversationsQueryHandler,
)
from application.conversations.services import GenerateAssistantReplyService
from domain.workspaces.entities import Permission, Role
from infrastructure.conversations.async_repository import (
    SqlAlchemyAsyncConversationRepository,
    SqlAlchemyAsyncMessageRepository,
)
from infrastructure.conversations.llm.anthropic_provider import AnthropicLLMProvider
from infrastructure.conversations.llm.ollama_provider import OllamaLLMProvider
from infrastructure.database.session import get_db
from presentation.api.auth.dependencies import get_current_user_id
from presentation.api.conversations.schemas import (
    ConversationResponse,
    MessageResponse,
    SendMessageRequest,
)
from presentation.api.search.router import get_search_handler
from presentation.api.workspaces.dependencies import require_permission

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/conversations", tags=["conversations"])

_llm = (
    AnthropicLLMProvider(
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5"),
    )
    if os.environ.get("LLM_PROVIDER", "local") == "anthropic"
    else OllamaLLMProvider(
        url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
        model=os.environ.get("OLLAMA_MODEL", "llama3.2:1b"),
    )
)


def get_create_conversation_handler(
    session: AsyncSession = Depends(get_db),
) -> CreateConversationCommandHandler:
    return CreateConversationCommandHandler(SqlAlchemyAsyncConversationRepository(session))


def get_list_conversations_handler(session: AsyncSession = Depends(get_db)) -> ListConversationsQueryHandler:
    return ListConversationsQueryHandler(SqlAlchemyAsyncConversationRepository(session))


def get_send_message_handler(session: AsyncSession = Depends(get_db)) -> SendUserMessageCommandHandler:
    return SendUserMessageCommandHandler(
        SqlAlchemyAsyncConversationRepository(session), SqlAlchemyAsyncMessageRepository(session)
    )


def get_messages_query_handler(session: AsyncSession = Depends(get_db)) -> GetConversationMessagesQueryHandler:
    return GetConversationMessagesQueryHandler(
        SqlAlchemyAsyncConversationRepository(session), SqlAlchemyAsyncMessageRepository(session)
    )


def get_reply_service(session: AsyncSession = Depends(get_db)) -> GenerateAssistantReplyService:
    return GenerateAssistantReplyService(
        SqlAlchemyAsyncConversationRepository(session),
        SqlAlchemyAsyncMessageRepository(session),
        get_search_handler(session),
        _llm,
    )


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    workspace_id: str,
    user_id: str = Depends(get_current_user_id),
    _role: Role = Depends(require_permission(Permission.VIEW_WORKSPACE)),
    handler: CreateConversationCommandHandler = Depends(get_create_conversation_handler),
) -> ConversationResponse:
    conversation_id = await handler.handle(CreateConversationCommand(workspace_id=workspace_id, user_id=user_id))
    return ConversationResponse(id=conversation_id)


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    workspace_id: str,
    user_id: str = Depends(get_current_user_id),
    _role: Role = Depends(require_permission(Permission.VIEW_WORKSPACE)),
    handler: ListConversationsQueryHandler = Depends(get_list_conversations_handler),
) -> list[ConversationResponse]:
    conversations = await handler.handle(ListConversationsQuery(workspace_id=workspace_id, user_id=user_id))
    return [ConversationResponse(id=c.id) for c in conversations]


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    workspace_id: str,
    conversation_id: str,
    user_id: str = Depends(get_current_user_id),
    _role: Role = Depends(require_permission(Permission.VIEW_WORKSPACE)),
    handler: GetConversationMessagesQueryHandler = Depends(get_messages_query_handler),
) -> list[MessageResponse]:
    messages = await handler.handle(
        GetConversationMessagesQuery(conversation_id=conversation_id, requesting_user_id=user_id)
    )
    return [
        MessageResponse(id=m.id, role=m.role, content=m.content, source_chunk_ids=m.source_chunk_ids)
        for m in messages
    ]


@router.post("/{conversation_id}/messages")
async def send_message(
    workspace_id: str,
    conversation_id: str,
    payload: SendMessageRequest,
    user_id: str = Depends(get_current_user_id),
    _role: Role = Depends(require_permission(Permission.VIEW_WORKSPACE)),
    send_handler: SendUserMessageCommandHandler = Depends(get_send_message_handler),
    reply_service: GenerateAssistantReplyService = Depends(get_reply_service),
) -> StreamingResponse:
    message_id = await send_handler.handle(
        SendUserMessageCommand(
            conversation_id=conversation_id, requesting_user_id=user_id, content=payload.content
        )
    )

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for delta in reply_service.stream(conversation_id=conversation_id, workspace_id=workspace_id):
                yield f"data: {json.dumps({'delta': delta})}\n\n"
        except Exception as exc:  # noqa: BLE001 — fail-fast boundary: any failure once
            # streaming has started (headers are already sent) must become an SSE
            # error event rather than an unhandled 500, so this is deliberately broad.
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            return
        yield f"data: {json.dumps({'done': True, 'message_id': message_id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
