from flask import Blueprint

bp = Blueprint('snapcast', __name__, url_prefix='/snapcast')

from . import (
    episode,  # noqa: E402
    views,  # noqa: E402
)
