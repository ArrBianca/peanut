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

bp = Blueprint("mane", __name__, template_folder="templates")


@bp.route("/")
def main_page():
    """Get the site's homepage."""
    return render_template("mainpage.html")


@bp.route("/dropbox")
def dropbox():
    """Get the site's homepage, but with the "Dropbox" checkbox checked."""
    return render_template("mainpage.html", dropbox="checked")


@bp.route("/upload", methods=["POST"])
def upload():
    """Handle file upload."""
    file = request.files["file"]
    if request.form.get("dropbox"):
        Thread(
            target=send_file,
            # Can't use the decorator because it tries to get the jmap global
            # or the config to create it, from the app context. Doesn't exist
            # in a thread. We have to pull it out here and pass it along.
            args=(get_jmap(), file.filename, file.read()),
            daemon=True,
        ).start()
        return redirect(url_for("mane.dropbox"))

    filename = perform_upload(file)
    if filename is not None:
        return render_template("fileuploaded.html", link=filename)
    return "Error, probably an empty upload field"


@bp.route("/uploadbot", methods=["POST"])
def bot_upload():
    """Handle file upload and return a simpler response for bots."""
    file = request.files["file"]
    filename = perform_upload(file)
    if filename is not None:
        return "http://f.peanut.one/" + filename
    return "Error, probably an empty upload field"


def perform_upload(file: FileStorage, custom_name: str | None = None):
    """Rename and upload file to Amazon S3, returning its new name."""
    if file is None or file.filename is None:
        return None

    filename = secure_filename(file.filename)
    ext = [x[-1] if len(x) > 1 else None for x in [filename.split(".")]][0]
    if custom_name is not None:
        result = db.session.execute(
            select(PeanutFile)
            .where(PeanutFile.filename == custom_name),
        ).fetchone()
        if result is not None:
            return None
        newname = custom_name
        if ext:
            newname += "." + ext
    else:
        newname = randomname(ext)

    file.seek(0, 2)
    size = file.tell()
    file.seek(0, 0)
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
        file, "f.peanut.one", newname,
        ExtraArgs={"ACL": "public-read", "ContentType": file.mimetype})

    return newname
