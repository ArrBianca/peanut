from flask import Blueprint

smalltext = Blueprint('txt', __name__)

from . import views
