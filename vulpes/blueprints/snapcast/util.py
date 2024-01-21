from datetime import datetime, timezone
from functools import wraps

from flask import abort, request
from sqlalchemy import select, update

from .models import Podcast
from ... import db


def authorization_required(func):
    """Check Bearer token of incoming requests, based on the podcast being accessed."""
    @wraps(func)
    def inner(*args, **kwargs):
        if not request.authorization:
            return abort(401)  # No authentication supplied.

        result = db.first_or_404(  # Invalid podcast ID.
            select(Podcast.auth_token)
            .where(Podcast.uuid == kwargs["podcast_uuid"]),
        )

        if request.authorization.token == str(result):
            return func(*args, **kwargs)
        return abort(401)  # Authentication not correct.

    return inner


def touch_podcast(podcast_uuid):
    """Update the last_modified field for a podcast. Called on cache-invalidating requests."""
    db.session.execute(
        update(Podcast)
        .where(Podcast.uuid == podcast_uuid)
        .values({Podcast.last_build_date: datetime.now(timezone.utc)}),
    )
