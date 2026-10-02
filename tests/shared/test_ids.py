from app.shared.ids import generate_id


def test_generate_id_is_26_chars() -> None:
    assert len(generate_id()) == 26


def test_generate_id_is_unique() -> None:
    assert generate_id() != generate_id()
