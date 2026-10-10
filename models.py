from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class URL(Base):
    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    original_url: Mapped[str] = mapped_column(
        String(2048), nullable=False
    )
    # The primary key provides unique IDs. The unique constraint protects against duplicate short codes, and the index helps the database find URLs quickly.
    short_code: Mapped[str] = mapped_column(
        String(16), unique=True, index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )