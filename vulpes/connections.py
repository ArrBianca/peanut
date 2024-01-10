from functools import wraps
from typing import Any

import click
from flask import current_app, g

from . import db
from .jmap import JMAPClient


def init_app(app):
    """Register functions to run during request lifecycle, and add db commands."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(db_test_data)


def init_db():
    """Reset the database and load the schema."""
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
    """Insert testing data into database."""
    init_db()
    db = get_db()

    with current_app.open_resource('db/testdata.sql') as f:
        db.executescript(f.read().decode('utf8'))
    click.echo("Inserted testing data.")


def get_db():
    """Just returns the same db object as always."""
    # I need to figure out what to do about this.
    return db


def close_db(e: Any = None):
    """Close the database connection.

    This is registered as a callback when a request context is ended and cleaned up.
    """
    db = g.pop('db', None)

    if db is not None:
        db.close()


def uses_db(func):
    """Wrap a function that accesses the database."""
    @wraps(func)
    def inner(*args, **kwargs):
        db = get_db()
        return func(db, *args, **kwargs)
    return inner


def get_jmap():
    """Create or return the configured JMAPClient."""
    if 'jmap' not in g:
        g.jmap = JMAPClient(
            current_app.config["JMAP_HOSTNAME"],
            current_app.config["JMAP_USERNAME"],
            current_app.config["JMAP_TOKEN"],
        )

    return g.jmap


def uses_jmap(func):
    """Wrap a function that needs to use JMAP."""
    @wraps(func)
    def inner(*args, **kwargs):
        client = get_jmap()
        return func(client, *args, **kwargs)
    return inner
