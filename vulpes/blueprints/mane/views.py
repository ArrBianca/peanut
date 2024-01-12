from datetime import datetime, timezone
from threading import Thread

from flask import Blueprint, redirect, render_template, request, url_for
from sqlalchemy import select
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .jmap import get_jmap
from .models import PeanutFile
from .util import get_amazon, randomname, send_file
from ... import db

bp = Blueprint('mane', __name__)


@bp.route('/')
def mainpage():
    """Get the site's homepage."""
    return render_template('mainpage.html')


@bp.route('/dropbox')
def dropbox():
    """Get the site's homepage, but with the "Dropbox" checkbox checked."""
    return render_template('mainpage.html', dropbox="checked")


@bp.route('/upload', methods=["POST"])
def upload():
    """Handle file upload."""
    f = request.files["file"]
    if request.form.get("dropbox"):
        Thread(
            target=send_file,
            # Can't use the decorator because it tries to get the jmap global
            # or the config to create it, from the app context. Doesn't exist
            # in a thread. We have to pull it out here and pass it along.
            args=(get_jmap(), f.filename, f.read()),
            daemon=True,
        ).start()
        return redirect(url_for('mane.dropbox'))

    filename = performupload(f)
    if filename is not None:
        return render_template("fileuploaded.html", link=filename)
    return "Error, probably an empty upload field"


@bp.route('/uploadbot', methods=["POST"])
def uploadbot():
    """Handle file upload and return a simpler response for automated access."""
    f = request.files["file"]
    filename = performupload(f)
    if filename is not None:
        return "http://f.peanut.one/" + filename
    return "Error, probably an empty upload field"


def performupload(f: FileStorage, customname: str = None):
    """Rename and upload file to Amazon S3, returning its new name."""
    if not f:
        return None

    filename = secure_filename(f.filename)
    ext = [x[-1] if len(x) > 1 else None for x in [filename.split('.')]][0]
    if customname is not None:
        result = db.session.execute(
            select(PeanutFile)
            .where(PeanutFile.filename == customname),
        ).fetchone()
        if result is not None:
            return None
        newname = customname + "." + ext
    else:
        newname = randomname(ext)

    f.seek(0, 2)
    size = f.tell()
    f.seek(0, 0)
    db.session.add(
        PeanutFile(
            filename=newname,
            size=size,
            origin_name=filename,
            tstamp=datetime.now(timezone.utc),
        ),
    )
    db.session.commit()
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
