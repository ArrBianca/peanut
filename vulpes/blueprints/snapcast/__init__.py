from flask import Blueprint

bp = Blueprint('snapcast', __name__, url_prefix='/snapcast')

from . import views  # noqa: E402