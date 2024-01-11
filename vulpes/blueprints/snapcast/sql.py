from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import update

from ... import db
from .models import Podcast


def touch_podcast(podcast_uuid: UUID):
    """Update the last_modified field for a podcast. Called on cache-invalidating requests."""
    db.session.execute(
        update(Podcast)
        .where(Podcast.uuid == podcast_uuid)
        .values({Podcast.last_modified: datetime.now(timezone.utc)}),
    )
