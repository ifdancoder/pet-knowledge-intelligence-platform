from unittest.mock import patch

from infrastructure.database.session import build_session_factory


def test_build_session_factory_instruments_its_engine_for_tracing() -> None:
    with patch("infrastructure.database.session.SQLAlchemyInstrumentor") as mock_instrumentor_cls:
        build_session_factory("postgresql+asyncpg://kip:kip@localhost:5434/kip")

    mock_instrumentor_cls.return_value.instrument.assert_called_once()
    _, kwargs = mock_instrumentor_cls.return_value.instrument.call_args
    assert "engine" in kwargs
