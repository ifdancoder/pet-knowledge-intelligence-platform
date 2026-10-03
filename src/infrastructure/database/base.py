import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from shared.ids import generate_id


class Base(DeclarativeBase):
    pass


class ULIDPrimaryKeyMixin:
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=generate_id)


class TimestampMixin:
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
