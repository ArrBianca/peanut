import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse, urlunparse
from uuid import UUID

import boto3
from flask import Flask, render_template, g, request, redirect, json
from flask.json.provider import JSONProvider
from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy.model import Model
from sqlalchemy import ForeignKey, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from werkzeug.middleware.proxy_fix import ProxyFix
from flask.json.provider import DefaultJSONProvider


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.wsgi_app = ProxyFix(app.wsgi_app)

    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'vulpes.sqlite'),
        SQLALCHEMY_DATABASE_URI="sqlite:///../instance/neo_vulpes.sqlite"

    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    if app.config['SERVER_NAME'] == 'peanut.one':
        app.url_map.default_subdomain = "www"

    db.init_app(app)
    with app.app_context():
        db.create_all()

    from . import connections
    connections.init_app(app)

    from .blueprints import mane, snapcast, twitch
    app.register_blueprint(mane.bp)
    app.register_blueprint(snapcast.bp)
    app.register_blueprint(twitch.bp)

    # @app.before_request
    def redirect_nonwww():
        """Redirect non-www requests to www.
        I think this is not necessary on NFS when configured with"""
        urlparts = urlparse(request.url)
        if urlparts.netloc == 'peanut.one':
            urlparts_list = list(urlparts)
            urlparts_list[1] = 'www.peanut.one'
            return redirect(urlunparse(urlparts_list), code=301)

    @app.errorhandler(404)
    def fower_oh_fower(e):
        return render_template("fower-oh-fower.html"), 404

    return app


def get_amazon():
    if 's3' not in g:
        g.s3 = boto3.client('s3')
    return g.s3
