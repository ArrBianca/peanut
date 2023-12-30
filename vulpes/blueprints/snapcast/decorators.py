from functools import wraps

from flask import abort, request

from .sql import SELECT_PODCAST_AUTH_KEY
from ...connections import get_db


def authorization_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if not request.authorization:
            return abort(401)  # No authentication supplied.

        db = get_db()
        result = db.execute(SELECT_PODCAST_AUTH_KEY, (kwargs['podcast_uuid'],)).fetchone()
        if result is None:
            return abort(404)  # Podcast not found.

        if request.authorization.token == result['auth_token']:
            return func(*args, **kwargs)
        else:
            return abort(401)  # Authentication not correct.
    return inner
