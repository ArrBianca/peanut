import string
from random import choice

from flask import current_app as app
from sqlalchemy import select

from ...connections import get_db
from ...nitre import PeanutFile


def randomname(ext=None):
    """Generate a new unique random short name for a file."""
    c = get_db()
    randname = ''.join([choice(string.ascii_lowercase)
                       for _ in range(app.config['FILE_NAME_LENGTH'])])
    if ext is not None:
        randname = randname + '.' + ext

    result = c.session.execute(
        select(PeanutFile)
        .where(PeanutFile.filename == randname),
    ).fetchone()
    if result is not None:
        return randomname(ext)
    else:
        return randname


# @uses_jmap
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
    jmap_client.attach_file_to_message(
        draft,
        file_data,
        filename)
    jmap_client.send(draft)
