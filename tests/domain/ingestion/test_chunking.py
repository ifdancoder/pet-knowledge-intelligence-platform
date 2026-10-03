from domain.ingestion.chunking import split_into_chunks


def test_short_text_is_a_single_chunk() -> None:
    chunks = split_into_chunks("hello world", target_size=1000, overlap=100)
    assert chunks == ["hello world"]


def test_long_text_splits_into_multiple_chunks() -> None:
    paragraph = "word " * 50  # ~250 chars
    text = "\n\n".join([paragraph] * 10)  # ~2500 chars
    chunks = split_into_chunks(text, target_size=1000, overlap=100)
    assert len(chunks) > 1
    assert all(len(chunk) <= 1000 + 100 for chunk in chunks)


def test_chunks_overlap() -> None:
    paragraph = "word " * 50
    text = "\n\n".join([paragraph] * 10)
    chunks = split_into_chunks(text, target_size=1000, overlap=100)
    # the tail of one chunk reappears at the head of the next
    first_tail = chunks[0][-50:]
    assert first_tail in chunks[1]


def test_empty_text_produces_no_chunks() -> None:
    assert split_into_chunks("", target_size=1000, overlap=100) == []
