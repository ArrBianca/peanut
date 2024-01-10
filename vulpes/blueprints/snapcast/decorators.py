from functools import wraps

from flask import abort, request
from sqlalchemy import select

from ...connections import get_db
from ...magus import Podcast


def authorization_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if not request.authorization:
            return abort(401)  # No authentication supplied.

        db = get_db()
        result = db.first_or_404(
            select(Podcast.auth_token)
            .where(Podcast.uuid == kwargs['podcast_uuid'])
        )

        if request.authorization.token == str(result):
            return func(*args, **kwargs)
        else:
            return abort(401)  # Authentication not correct.

    return inner
