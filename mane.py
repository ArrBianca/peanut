import string
import random
import time
from urllib.parse import urlparse, urlunparse

import sqlite3

from flask import Flask, render_template, request, redirect
from flask_basicauth import BasicAuth
from werkzeug.utils import secure_filename
from werkzeug.contrib.fixers import ProxyFix

from twitchapp import twitchapp
from rssapp import rssapp

import boto3

UNREGISTERED_MAX_SIZE = 25 * 1024 * 1024
ADMIN_MAX_SIZE = 25 * 1024 * 1024

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

app.url_map.default_subdomain = "www"

basic_auth = BasicAuth(app)
app.config.from_pyfile("instance/config.py")
app.config["MAX_CONTENT_LENGTH"] = UNREGISTERED_MAX_SIZE

# app.register_blueprint(twitchapp, url_prefix='/twitch')
app.register_blueprint(twitchapp, subdomain='twitch')
app.register_blueprint(rssapp, url_prefix='/rss')

# app.config["TWITCH_CLIENT_ID"] = TWITCH_CLIENT_ID
# app.jinja_env.lstrip_blocks = True
# app.jinja_env.trim_blocks = True

# amazon = tinys3.Connection(app.config["S3_ACCESS_KEY"],
#                           app.config["S3_SECRET_KEY"],
#                           default_bucket="f.peanut.one")
amazon = boto3.client('s3')

FILE_NAME_LENGTH = 3  # 6


@app.before_request
def redirect_nonwww():
    """Redirect non-www requests to www."""
    urlparts = urlparse(request.url)
    if urlparts.netloc == 'peanut.one':
        urlparts_list = list(urlparts)
        urlparts_list[1] = 'www.peanut.one'
        return redirect(urlunparse(urlparts_list), code=301)


# @app.before_request
def before_request():
    """ A now-unused function that would force HTTPS.
    Outdated with the move to DigitalOcean"""
    if request.url.startswith('http://'):
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)


# def uses_db(f):
#    # @wraps(f)
#    def inner(*args, **kwargs):
#        db = connect(
#            db=app.config["DB_DB"],
#            user=app.config["DB_USERNAME"],
#            password=app.config["DB_PASSWORD"],
#            host=app.config["DB_HOST"],
#            port=app.config["DB_PORT"]
#        )
#        c = db.cursor()
#        res = f(c, *args, **kwargs)
#        db.commit()
#        db.close()
#        return res
#    return inner

def uses_db(func):
    def inner(*args, **kwargs):
        db = sqlite3.connect("peanut.sqlite")
        c = db.cursor()
        res = func(c, *args, **kwargs)
        db.commit()
        db.close()
        return res
    return inner


@app.route('/')
def mainpage():
    return render_template('mainpage.html')


@app.route("/custom")
@basic_auth.required
def custommainpage():
    return render_template("custommainpage.html")


@app.route('/upload', methods=["POST"])
def upload():
    f = request.files["file"]
    filename = performupload(f)
    if filename is not None:
        return render_template("fileuploaded.html", link=filename)
    else:
        return "Error, probably an empty upload field"


@app.route('/uploadbot', methods=["POST"])
def uploadbot():
    f = request.files["file"]
    filename = performupload(f)
    if filename is not None:
        return "http://f.peanut.one/" + filename
    else:
        return "Error, probably an empty upload field"


@app.route("/customupload", methods=["POST"])
@basic_auth.required
def customupload():
    app.config["MAX_CONTENT_LENGTH"] = ADMIN_MAX_SIZE
    f = request.files["file"]
    customname = request.form["customname"]
    filename = performupload(f, customname)
    app.config["MAX_CONTENT_LENGTH"] = UNREGISTERED_MAX_SIZE
    if filename is not None:
        return render_template("fileuploaded.html", link=filename)
    else:
        return "Filename taken, try another"


@app.route("/listall")
@basic_auth.required
@uses_db
def listall(c):
    c.execute("SELECT filename, origin_name FROM peanut_files")
    results = c.fetchall()
    allfiles = [i[0] for i in results]
    origins = [i[1] for i in results]
    # print(allfiles)
    print(results)
    return render_template("allfiles.html",
                           filelist=allfiles,
                           realnames=origins)


@app.route("/ip")
def ip():
    """Returns simply the IP of the client."""
    return request.remote_addr
    # Stuff below is from before importing the werkzeug Proxy Fixer
    # The above line is now sufficient

    # if request.headers.getlist("X-Forwarded-For"):
    #     PAW's internal stuff can occlude original ip, fetch from here instead
    #     return request.headers.getlist("X-Forwarded-For")[0]
    # else:


@uses_db
def randomname(c, ext=None):
    randname = ''.join([random.choice(string.ascii_lowercase)
                        for _ in range(FILE_NAME_LENGTH)])
    if ext is not None:
        randname = randname + '.' + ext
    c.execute("SELECT * FROM peanut_files WHERE filename=?", (randname,))
    if c.fetchone() is not None:
        return randomname(ext)
    else:
        return randname


@uses_db
def performupload(c, f, customname=None):
    # f = request.files["file"]
    if not f:
        return None

    filename = secure_filename(f.filename)
    ext = [x[-1] if len(x) > 1 else None for x in [filename.split('.')]][0]
    if customname is not None:
        c.execute("SELECT * FROM peanut_files WHERE filename=?", (customname,))
        if c.fetchone() is not None:
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
    amazon.upload_fileobj(f, 'f.peanut.one', newname,
        ExtraArgs={'ACL': 'public-read', 'ContentType': f.mimetype})

    # deletewithinquota(c)
    return newname


# @uses_db
def deletewithinquota(c):
    maxarchive = 1024 * 1024 * 100

    c.execute("SELECT * from peanut_files ORDER BY tstamp")
    results = c.fetchall()
    takensize = sum(row[1] for row in results)

    if takensize > maxarchive:
        difference = takensize - maxarchive
        deleted = 0
        unlucky = []

        for row in results:
            if difference > deleted:
                unlucky.append(row[0])
                deleted += row[1]

        for filename in unlucky:
            amazon.delete(filename)
            c.execute("DELETE FROM peanut_files WHERE filename=?", (filename,))

        # c.executemany("DELETE FROM peanut_files WHERE filename=%s",
        #               [(x,) for x in unlucky])


@app.errorhandler(404)
def fower_oh_fower(e):
    return render_template("fower-oh-fower.html"), 404

if __name__ == "__main__":
    app.run(debug=True)
