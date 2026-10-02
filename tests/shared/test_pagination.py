from app.shared.pagination import Page


def test_page_serializes_generic_items() -> None:
    page = Page[int](items=[1, 2, 3], next_cursor="abc")
    assert page.model_dump() == {"items": [1, 2, 3], "next_cursor": "abc"}


def test_page_defaults_next_cursor_to_none() -> None:
    page = Page[str](items=["a"])
    assert page.next_cursor is None
