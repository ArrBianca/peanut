from datetime import datetime, timezone
from uuid import UUID

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select, update
from ...magus import Podcast, Episode

ADD_EPISODE = """
    INSERT INTO episode (podcast_uuid, title, subtitle, uuid, media_url,
                         media_size, media_type, media_duration, pub_date, link)
    VALUES (:podcast_uuid, :title, :subtitle, :uuid, :media_url,
            :media_size, :media_type, :media_duration, :pub_date, :link)"""
INSERT_EPISODE = """
    INSERT INTO episode (podcast_uuid, uuid, title, media_url, media_size, media_type, media_duration, pub_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
DELETE_EPISODE_BY_UUID = """DELETE FROM episode WHERE podcast_uuid=? AND uuid=?"""
# SELECT_EPISODE_LATEST = """SELECT * FROM episode WHERE podcast_uuid=? ORDER BY id DESC LIMIT 1"""
SELECT_EPISODE_LATEST = select(Episode).order_by(Episode.rowid)
SELECT_EPISODE_BY_ID = """SELECT * FROM episode WHERE podcast_uuid=? AND id=?"""
SELECT_EPISODE_BY_UUID = """SELECT * FROM episode WHERE podcast_uuid=? AND uuid=?"""
SELECT_PODCAST_AUTH_KEY = """SELECT auth_token FROM podcast WHERE uuid=?"""
SELECT_PODCAST_BY_UUID = """SELECT * FROM podcast WHERE uuid=?"""
SELECT_PODCAST_EPISODES = """SELECT * FROM episode WHERE podcast_uuid=?"""  # noqa: E501
LAST_MODIFIED_PATTERN = "%a, %d %b %Y %H:%M:%S %Z"


def touch_podcast(db: SQLAlchemy, podcast_uuid: UUID):
    db.session.execute(
        update(Podcast)
        .where(Podcast.uuid == podcast_uuid)
        .values({Podcast.last_modified: datetime.now(timezone.utc)})
    )
