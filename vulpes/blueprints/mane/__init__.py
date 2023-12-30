import random
import string
import time
from threading import Thread

from flask import (Blueprint, render_template, request,
                   current_app as app, redirect, url_for)
from werkzeug.utils import secure_filename

from vulpes import get_amazon
from vulpes.connections import get_db, uses_db, get_jmap

bp = Blueprint('mane', __name__)

QUERY_SELECT_BY_FILENAME = "SELECT * FROM peanut_files WHERE filename=?"


@bp.route('/')
def mainpage():
    return render_template('mainpage.html')


@bp.route('/dropbox')
def dropbox():
    return render_template('mainpage.html', dropbox="checked")


@bp.route('/upload', methods=["POST"])
def upload():
    f = request.files["file"]
    if request.form.get("dropbox"):
        Thread(
            target=send_file,
            # Can't use the decorator because it tries to get the jmap global
            # or the config to create it, from the app context. Doesn't exist
            # in a thread. We have to pull it out here and pass it along.
            args=(get_jmap(), f.filename, f.read()),
            daemon=True
        ).start()
        return redirect(url_for('mane.dropbox'))

    filename = performupload(f)
    if filename is not None:
        return render_template("fileuploaded.html", link=filename)
    else:
        return "Error, probably an empty upload field"


@bp.route('/uploadbot', methods=["POST"])
def uploadbot():
    f = request.files["file"]
    filename = performupload(f)
    if filename is not None:
        return "http://f.peanut.one/" + filename
    else:
        return "Error, probably an empty upload field"


def randomname(ext=None):
    c = get_db()
    randname = ''.join([random.choice(string.ascii_lowercase)
                       for _ in range(app.config['FILE_NAME_LENGTH'])])
    if ext is not None:
        randname = randname + '.' + ext
    if c.execute(QUERY_SELECT_BY_FILENAME, (randname,)).fetchone() is not None:
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
        body
    )
    jmap_client.attach_file_to_message(
        draft,
        file_data,
        filename)
    jmap_client.send(draft)


@uses_db
def performupload(db, f, customname=None):
    if not f:
        return None

    filename = secure_filename(f.filename)
    ext = [x[-1] if len(x) > 1 else None for x in [filename.split('.')]][0]
    if customname is not None:
        result = db.execute(QUERY_SELECT_BY_FILENAME, (customname,)).fetchone()
        if result is not None:
            return None
        else:
            newname = customname + "." + ext
    else:
        newname = randomname(ext)

    f.seek(0, 2)
    size = f.tell()
    f.seek(0, 0)
    db.execute("INSERT INTO peanut_files VALUES (?, ?, ?, ?)",
               (newname, size, filename, int(time.time())))
    db.commit()
    # amazon.upload(newname, f.stream)
    get_amazon().upload_fileobj(
        f, 'f.peanut.one', newname,
        ExtraArgs={'ACL': 'public-read', 'ContentType': f.mimetype})

    # deletewithinquota(c)
    return newname


# # @uses_db
# def deletewithinquota(c):
#     maxarchive = 1024 * 1024 * 100
#
#     c.execute("SELECT * from peanut_files ORDER BY tstamp")
#     results = c.fetchall()
#     takensize = sum(row[1] for row in results)
#
#     if takensize > maxarchive:
#         difference = takensize - maxarchive
#         deleted = 0
#         unlucky = []
#
#         for row in results:
#             if difference > deleted:
#                 unlucky.append(row[0])
#                 deleted += row[1]
#
#         for filename in unlucky:
#             amazon.delete(filename)
#             c.execute("DELETE FROM peanut_files WHERE filename=?", (filename,))
#
#         # c.executemany("DELETE FROM peanut_files WHERE filename=%s",
#         #               [(x,) for x in unlucky])