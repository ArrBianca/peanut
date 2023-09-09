from flask import current_app, g
from functools import wraps
import sqlite3


def uses_db(func):
    @wraps(func)
    def inner(*args, **kwargs):
        # db = sqlite3.connect("peanut.sqlite")
        db = sqlite3.connect(current_app.config['DATABASE'])
        c: sqlite3.Cursor = db.cursor()
        res = func(c, *args, **kwargs)
        db.commit()
        db.close()
        return res

    return inner


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db(app):
    app.teardown_appcontext(close_db)
