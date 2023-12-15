import random
import string
import time

from flask import Blueprint, render_template, request, current_app as app, redirect, url_for
from requests import post

from vulpes.connections import get_db, uses_db

from vulpes.tiny_jmap_library import TinyJMAPClient
from werkzeug.utils import secure_filename

from vulpes import get_amazon

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
        send_file(f)
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


def send_file(f):
    f.seek(0, 2)
    size = f.tell()
    f.seek(0, 0)

    client = TinyJMAPClient(
        hostname=app.config["JMAP_HOSTNAME"],
        username=app.config["JMAP_USERNAME"],
        token=app.config["JMAP_TOKEN"],
    )

    account_id = client.get_account_id()
    identity_id = client.get_identity_id()

    uploaded = post(
        f"https://api.fastmail.com/jmap/upload/{account_id}/",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {client.token}",
        },
        data=f.read()
    ).json()

    body = f"""Hi June!

Someone just uploaded a file to the dropbox!

Original filename: {f.filename}
Filesize: {size / 1024 / 1024:.2F}MB

Rad.
"""

    query_res = client.make_jmap_call(
        {
            "using": ["urn:ietf:params:jmap:core", "urn:ietf:params:jmap:mail"],
            "methodCalls": [
                [
                    "Mailbox/query",
                    {"accountId": account_id, "filter": {"name": "Drafts"}},
                    "a",
                ]
            ],
        }
    )

    # Pull out the id from the list response, and make sure we got it
    draft_mailbox_id = query_res["methodResponses"][0][1]["ids"][0]
    assert len(draft_mailbox_id) > 0

    draft = {
        "from": [{"email": "peanut@peanut.one"}],
        "to": [{"email": "june@peanut.one"}],
        "subject": "File for ya!",
        "keywords": {"$draft": True},
        "mailboxIds": {draft_mailbox_id: True},
        "bodyValues": {"body": {"value": body, "charset": "utf-8"}},
        "textBody": [{"partId": "body", "type": "text/plain"}],
        "attachments": [{"blobId": uploaded["blobId"], "type": uploaded["type"], "name": f.filename}]
    }

    client.make_jmap_call(
        {
            "using": ["urn:ietf:params:jmap:core",
                      "urn:ietf:params:jmap:mail",
                      "urn:ietf:params:jmap:submission"
                      ],
            "methodCalls": [
                ["Email/set", {"accountId": account_id, "create": {"draft": draft}}, "a"],
                [
                    "EmailSubmission/set",
                    {
                        "accountId": account_id,
                        "onSuccessDestroyEmail": ["#sendIt"],
                        "create": {
                            "sendIt": {
                                "emailId": "#draft",
                                "identityId": identity_id,
                            }
                        },
                    },
                    "b",
                ],
            ],
        }
    )


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
