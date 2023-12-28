from datetime import datetime, timedelta, timezone
from functools import wraps
from uuid import uuid4

from flask import Blueprint, Response, request, jsonify, abort
from podgen import Podcast, Episode, Media, Person, Category

from vulpes.connections import uses_db, get_db

bp = Blueprint('snapcast', __name__, url_prefix='/snapcast')

ADD_EPISODE = """
    INSERT INTO episode (podcast_uuid, title, subtitle, uuid, media_url,
                         media_size, media_type, media_duration, pub_date, link)
    VALUES (:podcast_uuid, :title, :subtitle, :uuid, :media_url,
            :media_size, :media_type, :media_duration, :pub_date, :link)"""
INSERT_EPISODE = """
    INSERT INTO episode (podcast_uuid, uuid, title, media_url, media_size, media_type, media_duration, pub_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
DELETE_EPISODE_BY_UUID = """DELETE FROM episode WHERE podcast_uuid=? AND uuid=?"""
SELECT_EPISODE_LATEST = """SELECT * FROM episode WHERE podcast_uuid=? ORDER BY id DESC LIMIT 1"""
SELECT_EPISODE_BY_ID = """SELECT * FROM episode WHERE podcast_uuid=? AND id=?"""
SELECT_EPISODE_BY_UUID = """SELECT * FROM episode WHERE podcast_uuid=? AND uuid=?"""
SELECT_PODCAST_AUTH_KEY = """SELECT auth_token FROM podcast WHERE uuid=?"""
SELECT_PODCAST_BY_UUID = """SELECT * FROM podcast WHERE uuid=?"""
SELECT_PODCAST_EPISODES = """SELECT * FROM episode WHERE podcast_uuid=?"""  # noqa: E501
LAST_MODIFIED_PATTERN = "%a, %d %b %Y %H:%M:%S %Z"


def authorization_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        print(args, kwargs)
        if not request.authorization:
            return abort(401)  # No authentication supplied.

        db = get_db()
        result = db.execute(SELECT_PODCAST_AUTH_KEY, (kwargs['podcast_uuid'],)).fetchone()
        if result is None:
            return abort(404)  # Podcast not found.

        if request.authorization.token == result['auth_token']:
            return func(*args, **kwargs)
        else:
            return abort(401)  # Authentication not correct.
    return inner


@bp.route("/<feed_id>/feed.xml", methods=["GET"])
@uses_db
def generate_feed(db, feed_id):
    cast = db.execute(SELECT_PODCAST_BY_UUID, (feed_id,)).fetchone()

    last_modified = datetime.fromisoformat(cast['last_modified'])
    if since := request.if_modified_since:
        # The database column stores microseconds which aren't included in the
        # request. If they're just about equal we don't update anything.
        if (last_modified - since).total_seconds() < 1:
            return Response(status=304)

    p = Podcast(
        name=cast['name'],
        description=cast['description'],
        website=cast['website'],
        category=Category(cast['category']),
        language="en-US",
        explicit=cast['explicit'],
        image=cast['image'],
        authors=[Person(name=cast['author_name'])],
        withhold_from_itunes=bool(cast['withhold_from_itunes']),
        last_updated=last_modified,
    )

    res = db.execute("SELECT * FROM episode WHERE podcast_uuid=?", (cast['uuid'],))
    episodes = res.fetchall()
    for episode in episodes:
        if media_duration := episode['media_duration']:
            media_duration = timedelta(seconds=media_duration)

        e = Episode(
            id=episode['uuid'],
            title=episode['title'],
            summary=episode['summary'],
            subtitle=episode['subtitle'],
            long_summary=episode['long_summary'],
            media=Media(
                episode['media_url'],
                size=episode['media_size'],
                type=episode['media_type'],
                duration=media_duration,
            ),
            publication_date=datetime.fromisoformat(episode['pub_date']),
            link=episode['link'],
            image=episode['episode_art']
        )
        p.add_episode(e)

    response = Response(p.rss_str(), mimetype='text/xml')
    response.last_modified = last_modified
    return response


@bp.route("/<podcast_uuid>/feed.xml", methods=["HEAD"])
@uses_db
def feed_head(db, podcast_uuid):
    cast = db.execute(SELECT_PODCAST_BY_UUID, (podcast_uuid,)).fetchone()
    response = Response()
    response.last_modified = datetime.fromisoformat(cast['last_modified'])
    return response


@bp.route("/snapcast.xml")
def generate_snapcast():
    """shortcut!"""
    if request.method == "HEAD":
        return feed_head("1787bd99-9d00-48c3-b763-5837f8652bd9")
    else:
        return generate_feed('1787bd99-9d00-48c3-b763-5837f8652bd9')


@bp.route("/snapcast/add_test")
@uses_db
def snapcast_test(db):
    data = {
        "podcast_id": 1,
        "title": "Test Episode3",
        "subtitle": None,
        "uuid": str(uuid4()),
        "media_url": "https://f005.backblazeb2.com/file/jbc-external/test_episode_2.mp3",
        "media_size": 9817898,
        "media_type": "audio/mpeg",
        "media_duration": timedelta(seconds=242).total_seconds(),
        "pub_date": datetime.now(timezone.utc),
        "link": None
    }
    db.execute(ADD_EPISODE, data)
    db.execute(
        "UPDATE podcast SET last_modified = ? WHERE id = 1",
        (datetime.now(timezone.utc),)
    )
    db.commit()
    return "ok."


@bp.route("/<podcast_uuid>/publish", methods=["POST"])
@authorization_required
@uses_db
def publish_episode(db, podcast_uuid):
    """
    Required elements in JSON request body:
        url:       str,
        size:      int,
        ftype:     str,
    Optional elements:
        duration:  int,
        title:     str,
        subtitle:  str,
        link:      str,
        timestamp: int,
    """
    json = request.json

    if timestamp := json.get('timestamp'):
        pub_date = datetime.fromtimestamp(timestamp, timezone.utc)
    else:
        pub_date = datetime.now(timezone.utc)

    data = {
        "podcast_uuid":     podcast_uuid,
        "title":            json.get('title', "Untitled Episode"),
        "subtitle":         json.get('subtitle'),

        "uuid":             str(uuid4()),
        "media_url":        json['url'],
        "media_size":       json['size'],
        "media_type":       json['ftype'],
        "media_duration":   json.get('duration'),

        "link":             json.get('link'),
        "pub_date":         pub_date,
    }

    db.execute(ADD_EPISODE, data)
    db.execute(
        "UPDATE podcast SET last_modified = ? WHERE uuid = ?",
        (datetime.now(timezone.utc), podcast_uuid)
    )
    db.commit()
    return jsonify(success=True)


@bp.route("/<podcast_uuid>/episode/<episode_id>", methods=["GET"])
@uses_db
def get_episode(db, podcast_uuid, episode_id):
    """Fetches details of a specific episode.

    Either an integer episode number,a UUID, or `-1` which returns the latest
    episode.
    """
    try:
        episode_id = int(episode_id)
        if episode_id == -1:  # Special case: get the latest episode
            result = db.execute(SELECT_EPISODE_LATEST, (podcast_uuid,)).fetchone()
        else:
            result = db.execute(SELECT_EPISODE_BY_ID, (podcast_uuid, episode_id)).fetchone()
    except ValueError:  # Not integer-y, so a UUID probably.
        result = db.execute(SELECT_EPISODE_BY_UUID, (podcast_uuid, episode_id)).fetchone()

    if result is None:
        return abort(404)
    else:
        return jsonify(dict(result))


@bp.route("/<podcast_uuid>/episode/<episode_uuid>", methods=["PATCH"])
@uses_db
@authorization_required
def patch_episode(db, podcast_uuid, episode_uuid):
    """Just give it a dict with key=rowname value=newvalue. let's get naïve"""
    json = request.json

    rows = 0
    for key in json.keys():
        # By all accounts, something that should not ever be done
        result = db.execute(f"UPDATE episode SET {key}=? WHERE podcast_uuid=? AND uuid=?",
                            (json[key], podcast_uuid, episode_uuid))
        rows += result.rowcount
    db.execute(
        "UPDATE podcast SET last_modified=? WHERE uuid=?",
        (datetime.now(timezone.utc), podcast_uuid)
    )
    db.commit()

    return jsonify(success=True, rows=rows)


@bp.route("/<podcast_uuid>/episode/<episode_uuid>", methods=["DELETE"])
@authorization_required
@uses_db
def delete_episode(db, podcast_uuid, episode_uuid):
    result = db.execute(DELETE_EPISODE_BY_UUID, (podcast_uuid, episode_uuid))
    db.execute(
        "UPDATE podcast SET last_modified=? WHERE uuid=?",
        (datetime.now(timezone.utc), podcast_uuid)
    )
    db.commit()

    if result.rowcount == 0:
        return abort(404)
    else:
        return jsonify(success=True)


@bp.route("/<podcast_uuid>/episodes", methods=["GET"])
@authorization_required
@uses_db
def get_all_episodes(db, podcast_uuid):
    results = db.execute(SELECT_PODCAST_EPISODES, (podcast_uuid,))

    return jsonify([dict(row) for row in results.fetchall()])
