from domain.conversations.entities import Conversation, Message


def test_conversation_create_assigns_an_id() -> None:
    conversation = Conversation.create(workspace_id="w1", user_id="u1")
    assert len(conversation.id) == 26
    assert conversation.workspace_id == "w1"
    assert conversation.user_id == "u1"


def test_message_from_user_has_no_source_chunks() -> None:
    message = Message.from_user(conversation_id="c1", content="hello")
    assert len(message.id) == 26
    assert message.role == "user"
    assert message.content == "hello"
    assert message.source_chunk_ids == []


def test_message_from_assistant_records_source_chunks() -> None:
    message = Message.from_assistant(conversation_id="c1", content="hi there", source_chunk_ids=["ch1", "ch2"])
    assert message.role == "assistant"
    assert message.source_chunk_ids == ["ch1", "ch2"]
