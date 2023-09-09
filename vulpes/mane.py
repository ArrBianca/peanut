import random
import string
import time

from flask import Blueprint, render_template, request, current_app
from connections import get_db

from werkzeug.utils import secure_filename

from vulpes import get_amazon

bp = Blueprint('mane', __name__)


@bp.route('/')
def mainpage():
    print(get_amazon())
    return render_template('mainpage.html')


@bp.route('/upload', methods=["POST"])
def upload():
    f = request.files["file"]
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
                        for _ in range(current_app.config['FILE_NAME_LENGTH'])])
    if ext is not None:
        randname = randname + '.' + ext
    if c.execute("SELECT * FROM peanut_files WHERE filename=?", (randname,)).fetchone() is not None:
        return randomname(ext)
    else:
        return randname


def performupload(f, customname=None):
    c = get_db()
    if not f:
        return None

    filename = secure_filename(f.filename)
    ext = [x[-1] if len(x) > 1 else None for x in [filename.split('.')]][0]
    if customname is not None:
        if (c.execute("SELECT * FROM peanut_files WHERE filename=?", (customname,))
                .fetchone() is not None):
            return None
        else:
            newname = customname + "." + ext
    else:
        # noinspection PyTypeChecker
        newname = randomname(ext)

    f.seek(0, 2)
    size = f.tell()
    f.seek(0, 0)
    c.execute("INSERT INTO peanut_files VALUES (?, ?, ?, ?)",
              (newname, size, filename, time.time()))
    # amazon.upload(newname, f.stream)
    get_amazon().upload_fileobj(f, 'f.peanut.one', newname,
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

