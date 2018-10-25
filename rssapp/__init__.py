from flask import Blueprint

rssapp = Blueprint('rss', __name__)

from . import views
