from flask import Blueprint

bp = Blueprint('twitch', __name__, url_prefix="/twitch")

from . import views  # noqa: E402
