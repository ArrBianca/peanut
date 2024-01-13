import string
from random import choice

import boto3
from flask import current_app as app
from flask import g
from sqlalchemy import select

from .models import PeanutFile
from ... import db


def randomname(ext=None):
    """Generate a new unique random short name for a file."""
    randname = ''.join([choice(string.ascii_lowercase)
                       for _ in range(app.config['FOX']['FILE_NAME_LENGTH'])])
    if ext is not None:
        randname = randname + '.' + ext

    result = db.session.execute(
        select(PeanutFile)
        .where(PeanutFile.filename == randname),
    ).fetchone()
    if result is not None:
        return randomname(ext)
    return randname


def send_file(jmap_client, filename, file_data):
    """Email June a file!

    :type jmap_client: vulpes.jmap.JMAPClient
    :type filename: str
    :type file_data: bytes
    """
    body = f"""Hi June,

Someone just uploaded a file to the dropbox!

Original filename: {filename}
Filesize: {len(file_data) / 1024 / 1024:.2F}MB

"""
    draft = jmap_client.prepare_plaintext_email(
        "june@peanut.one",
        "File for ya!",
        body,
    )
    jmap_client.attach_file_to_message(draft, file_data, filename)
    jmap_client.send(draft)


def get_amazon():
    """Get an s3 connection."""
    if 's3' not in g:
        g.s3 = boto3.client(
            's3',
            access_key_id=app.config['S3']['ACCESS_KEY'],
            secret_access_key=app.config['S3']['SECRET_KEY'],
        )
    return g.s3
