from ulid import ULID


def generate_id() -> str:
    return str(ULID())
