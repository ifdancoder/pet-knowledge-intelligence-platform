def split_into_chunks(text: str, *, target_size: int = 1000, overlap: int = 100) -> list[str]:
    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= target_size or not current:
            current = candidate
        else:
            chunks.append(current)
            overlap_tail = current[-overlap:] if overlap else ""
            current = f"{overlap_tail}\n\n{paragraph}" if overlap_tail else paragraph

    if current:
        chunks.append(current)

    return chunks
