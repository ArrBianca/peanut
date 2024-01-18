from datetime import datetime, timedelta, timezone
from typing import List, Literal, Optional
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vulpes.blueprints.snapcast.jxml import FeedItem, PodcastFeed

from ... import db


class DatetimeFormattingModel:
    """Parent class that allows a Model to turn into a jsonify-able dictionary.

    Add to the converter here for any more non-serializable data types.
    """

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


class Podcast(DatetimeFormattingModel, db.Model, PodcastFeed):
    """ORM Mapping for the database's `podcast` table."""

    __tablename__ = 'podcast'

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUID]
    title: Mapped[str]
    link: Mapped[str]
    description: Mapped[str]
    explicit: Mapped[bool]
    image: Mapped[str]
    author: Mapped[str]
    copyright: Mapped[Optional[str]]
    language: Mapped[str] = mapped_column(default="en-US")
    feed_url: Mapped[Optional[str]]
    categories: Mapped[List["Category"]] = relationship()
    itunes_block: Mapped[bool] = mapped_column(default=False)
    new_feed_url: Mapped[Optional[str]]
    complete: Mapped[bool] = mapped_column(default=False)
    auth_token: Mapped[UUID]
    last_build_date: Mapped[Optional[datetime]]
    is_serial: Mapped[bool] = mapped_column(default=False)
    episodes: Mapped[List["Episode"]] = relationship(
        back_populates="podcast", order_by="Episode.pub_date")


class Episode(FeedItem, DatetimeFormattingModel, db.Model):
    """ORM Mapping for the database's `episode` table."""

    __tablename__ = 'episode'

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUID]
    podcast_uuid = mapped_column(ForeignKey(Podcast.uuid))
    podcast: Mapped["Podcast"] = relationship(back_populates="episodes")
    title: Mapped[str]
    subtitle: Mapped[Optional[str]]
    description: Mapped[Optional[str]]
    media_url: Mapped[str]
    media_size: Mapped[int]
    media_type: Mapped[str]
    media_duration: Mapped[Optional[timedelta]]
    pub_date: Mapped[datetime]
    link: Mapped[Optional[str]]
    image: Mapped[Optional[str]]
    episode_type: Mapped[Literal["full", "trailer", "bonus"]] = mapped_column(default=None)
    season: Mapped[Optional[int]]
    episode: Mapped[Optional[int]]

    def __init__(self, **kwargs):
        for attr, value in kwargs.items():
            setattr(self, attr, value)
        # super().__init__()


class Category(DatetimeFormattingModel, db.Model):
    """ORM Mapping for the database's `category` table."""

    __tablename__ = 'category'

    id: Mapped[int] = mapped_column(primary_key=True)
    podcast_id: Mapped[int] = mapped_column(ForeignKey("podcast.id"))
    cat: Mapped[str]
    sub: Mapped[Optional[str]]

    # def __init__(self):
    #     self.__dict__['cat'] = self.cat
    #     self.__dict__['sub'] = self.sub
