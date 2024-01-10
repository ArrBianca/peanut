from functools import wraps
from typing import Any

import click
from flask import current_app, g

from . import db
from .jmap import JMAPClient


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(db_test_data)


def init_db():
    db = get_db()

    with current_app.open_resource('db/schema.sql') as f:
        db.executescript(f.read().decode('utf8'))


@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')


@click.command('dummy-db')
def db_test_data():
    """Insert testing data into database"""
    init_db()
    db = get_db()

    with current_app.open_resource('db/testdata.sql') as f:
        db.executescript(f.read().decode('utf8'))
    click.echo("Inserted testing data.")


def get_db():
    # if 'db' not in g:
    #     g.db = sqlite3.connect(
    #         current_app.config['DATABASE'],
    #         detect_types=sqlite3.PARSE_DECLTYPES
    #     )
    #     g.db.row_factory = sqlite3.Row
    #
    # return g.db
    return db


def close_db(e: Any = None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def uses_db(func):
    @wraps(func)
    def inner(*args, **kwargs):
        db = get_db()
        return func(db, *args, **kwargs)
    return inner


def get_jmap():
    if 'jmap' not in g:
        g.jmap = JMAPClient(
            current_app.config["JMAP_HOSTNAME"],
            current_app.config["JMAP_USERNAME"],
            current_app.config["JMAP_TOKEN"],
        )

    return g.jmap


def uses_jmap(func):
    @wraps(func)
    def inner(*args, **kwargs):
        client = get_jmap()
        return func(client, *args, **kwargs)
    return inner
