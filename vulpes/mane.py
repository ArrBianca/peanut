import random
import string
import time

from flask import Blueprint, render_template, request, current_app as app
from vulpes.connections import get_db

from vulpes.tiny_jmap_library import TinyJMAPClient
from werkzeug.utils import secure_filename

from vulpes import get_amazon

bp = Blueprint('mane', __name__)

QUERY_SELECT_BY_FILENAME = "SELECT * FROM peanut_files WHERE filename=?"


@bp.route('/')
def mainpage():
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
                       for _ in range(app.config['FILE_NAME_LENGTH'])])
    if ext is not None:
        randname = randname + '.' + ext
    if c.execute(QUERY_SELECT_BY_FILENAME, (randname,)).fetchone() is not None:
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
        result = c.execute(QUERY_SELECT_BY_FILENAME, (customname,)).fetchone()
        if result is not None:
            return None
        else:
            newname = customname + "." + ext
    else:
        newname = randomname(ext)

    f.seek(0, 2)
    size = f.tell()
    f.seek(0, 0)
    c.execute("INSERT INTO peanut_files VALUES (?, ?, ?, ?)",
              (newname, size, filename, time.time()))
    # amazon.upload(newname, f.stream)
    get_amazon().upload_fileobj(
        f, 'f.peanut.one', newname,
        ExtraArgs={'ACL': 'public-read', 'ContentType': f.mimetype})

    client = TinyJMAPClient(
        hostname=app.config["JMAP_HOSTNAME"],
        username=app.config["JMAP_USERNAME"],
        token=app.config["JMAP_TOKEN"],
    )

    account_id = client.get_account_id()
    identity_id = client.get_identity_id()

    body = f"""
    Hi June!

    Someone just uploaded a file to peanut.one!

    Original filename: {filename}
    Filesize: {size / 1024 / 1024:.2F}MB
    Linky Linky: http://f.peanut.one/{newname}

    Rad.

    I can also tell you that, as far as I can tell, the upload came from {request.remote_addr} though it's likely obscured.

    Anyway, that's everything. Thanks for your time,
    -- Peanut
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
