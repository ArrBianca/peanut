from datetime import datetime, timedelta, timezone
from datetime import datetime, timedelta, timezone
from pprint import pformat as pf
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from . import db


class Podcast(db.Model):
    __tablename__ = 'podcast'

    rowid: Mapped[int] = mapped_column(primary_key=True)
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

    def as_dict(self):
        d = {}
        for col in self.__table__.columns:
            val = getattr(self, col.name)
            if isinstance(val, timedelta):
                d[col.name] = val.total_seconds()
            elif isinstance(val, datetime):
                d[col.name] = val.replace(tzinfo=timezone.utc).isoformat()
            else:
                d[col.name] = val
        return d

    def __init__(self, **kwargs):
        for attr, value in kwargs.items():
            setattr(self, attr, value)

    def __str__(self):
        output = {}
        for c in self.__table__.columns:
            output[c.name] = getattr(self, c.name)
        return pf(output)

    def __getitem__(self, item):
        return getattr(self, item)



class Episode(db.Model):
    __tablename__ = 'episode'

    rowid: Mapped[int] = mapped_column(primary_key=True)
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

    def as_dict(self):
        d = {}
        for col in self.__table__.columns:
            val = getattr(self, col.name)
            if isinstance(val, timedelta):
                d[col.name] = val.total_seconds()
            elif isinstance(val, datetime):
                d[col.name] = val.replace(tzinfo=timezone.utc).isoformat()
            else:
                d[col.name] = val
        return d

    def __init__(self, **kwargs):
        for attr, value in kwargs.items():
            setattr(self, attr, value)

    def __str__(self):
        output = {}
        for c in self.__table__.columns:
            output[c.name] = getattr(self, c.name)
        return pf(output)

    def __getitem__(self, item):
        if isinstance(item, str):
            return getattr(self, item)
        return self.__table__.columns[item]

    def keys(self):
        return self.__table__.columns.keys()

    __table_args__ = (
        CheckConstraint('title IS NOT NULL OR summary IS NOT NULL',
                        name='title_summary_check'),
    )


class Files(db.Model):
    __tablename__ = 'peanunt_files'

    rowid: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[Optional[str]]
    size: Mapped[Optional[int]]
    origin_name: Mapped[Optional[str]]
    tstamp: Mapped[Optional[datetime]]

    def __init__(self, **kwargs):
        for attr, value in kwargs.items():
            setattr(self, attr, value)
