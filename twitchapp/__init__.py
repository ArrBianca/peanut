from flask import Blueprint

twitchapp = Blueprint('twitch', __name__, template_folder='templates', static_folder='static')

from . import views
