from functools import wraps

from flask import abort, request
from sqlalchemy import select

from .sql import SELECT_PODCAST_AUTH_KEY
from ...connections import get_db
from ...magus import Podcast
from uuid import UUID


def authorization_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        print(args, kwargs)
        if not request.authorization:
            return abort(401)  # No authentication supplied.

        db = get_db()
        result = db.first_or_404(
            select(Podcast.auth_token)
            .where(Podcast.uuid == kwargs['podcast_uuid'])
        )
        print(result)
        print(request.authorization.token)
        if result is None:
            return abort(404)  # Podcast not found.

        if request.authorization.token == str(result):
            return func(*args, **kwargs)
        else:
            return abort(401)  # Authentication not correct.
    return inner
