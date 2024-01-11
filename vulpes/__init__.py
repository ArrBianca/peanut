import contextlib
import os

import boto3
from flask import Flask, g, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix


class Base(DeclarativeBase):
    """The DeclarativeBase you have to use in sqlalchemy."""

    pass


db = SQLAlchemy(model_class=Base)


def create_app(test_config=None):
    """Build the app object."""
    app = Flask(__name__, instance_relative_config=True)
    app.wsgi_app = ProxyFix(app.wsgi_app)

    app.config.from_mapping(
        SECRET_KEY='dev',
        SQLALCHEMY_DATABASE_URI=os.path.join("sqlite:///" + app.instance_path, 'nitre.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    with contextlib.suppress(OSError):
        os.makedirs(app.instance_path)

    if app.config['SERVER_NAME'] == 'peanut.one':
        app.url_map.default_subdomain = "www"

    db.init_app(app)

    from .blueprints import mane, snapcast, twitch
    app.register_blueprint(mane.bp)
    app.register_blueprint(snapcast.bp)
    app.register_blueprint(twitch.bp)

    @app.errorhandler(404)
    def fower_oh_fower(e):
        return render_template("fower-oh-fower.html"), 404

    return app


def get_amazon():
    """Get an s3 connection."""
    if 's3' not in g:
        g.s3 = boto3.client('s3')
    return g.s3
