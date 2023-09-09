import os
from urllib.parse import urlparse, urlunparse

import boto3
from flask import Flask, render_template, g, request, redirect


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'peanut.sqlite'),
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

    from . import connections
    app.teardown_appcontext(connections.close_db)

    from . import mane, twitch, podcast
    app.register_blueprint(mane.bp)
    app.register_blueprint(twitch.bp)
    app.register_blueprint(podcast.bp)

    @app.before_request
    def redirect_nonwww():
        """Redirect non-www requests to www."""
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
