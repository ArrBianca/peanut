from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column

from ... import db


class PeanutFile(db.Model):
    """ORM Mapping for the database's `peanut_file` table."""

    __tablename__ = 'peanut_file'

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[Optional[str]]
    size: Mapped[Optional[int]]
    origin_name: Mapped[Optional[str]]
    tstamp: Mapped[Optional[datetime]]

    def __init__(self, **kwargs):
        for attr, value in kwargs.items():
            setattr(self, attr, value)
