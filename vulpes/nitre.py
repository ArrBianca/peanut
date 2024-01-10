from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    """The DeclarativeBase you have to use in sqlalchemy."""

    pass


db = SQLAlchemy(model_class=Base)


class DatetimeFormattingModel:
    """Parent class that allows a Model to turn into a jsonify-able dictionary."""

    __table__ = None

    def as_dict(self):
        """Create a `dict` representation off the model.

        Replaces `datetime` and `timedelta` types with string representations, safe to send.
        """
        d = {}
        for col in self.__table__.columns:
            val = getattr(self, col.name)
            if isinstance(val, timedelta):
                d[col.name] = int(val.total_seconds())
            elif isinstance(val, datetime):
                d[col.name] = val.replace(tzinfo=timezone.utc).isoformat()
            else:
                d[col.name] = val
        return d


class Podcast(DatetimeFormattingModel, db.Model):
    """ORM Mapping for the database's `podcast` table."""

    __tablename__ = 'podcast'

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUID]
    name: Mapped[str]
    website: Mapped[str]
    description: Mapped[str]
    explicit: Mapped[bool]
    image: Mapped[str]
    author_name: Mapped[str]
    copyright: Mapped[Optional[str]]
    language: Mapped[str] = mapped_column(default="en-US")
    feed_url: Mapped[Optional[str]]
    category: Mapped[Optional[str]]
    withhold_from_itunes: Mapped[bool] = mapped_column(default=False)
    auth_token: Mapped[UUID]
    last_modified: Mapped[Optional[datetime]]
    is_serial: Mapped[Optional[bool]]

    def __init__(self, **kwargs):
        for attr, value in kwargs.items():
            setattr(self, attr, value)


class Episode(DatetimeFormattingModel, db.Model):
    """ORM Mapping for the database's `episode` table."""

    __tablename__ = 'episode'

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUID]
    podcast_uuid = mapped_column(ForeignKey(Podcast.uuid))
    title: Mapped[Optional[str]]
    summary: Mapped[Optional[str]]
    subtitle: Mapped[Optional[str]]
    long_summary: Mapped[Optional[str]]
    media_url: Mapped[str]
    media_size: Mapped[int]
    media_type: Mapped[str]
    media_duration: Mapped[Optional[timedelta]]
    pub_date: Mapped[datetime]
    link: Mapped[Optional[str]]
    episode_art: Mapped[Optional[str]]

    def __init__(self, **kwargs):
        for attr, value in kwargs.items():
            setattr(self, attr, value)

    __table_args__ = (
        CheckConstraint('title IS NOT NULL OR summary IS NOT NULL',
                        name='title_summary_check'),
    )


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
