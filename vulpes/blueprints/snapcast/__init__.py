from flask import Blueprint

bp = Blueprint('snapcast', __name__, url_prefix='/snapcast')

from . import episode  # noqa: E402, F401, I001 dang ruf really hates this pattern huh.
from . import views  # noqa: E402, F401
from . import models  # noqa: E402, F401
