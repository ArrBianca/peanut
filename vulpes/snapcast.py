from datetime import datetime, timedelta, timezone
from functools import wraps
from uuid import uuid4

from flask import Blueprint, Response, request, jsonify, current_app, abort
from podgen import Podcast, Episode, Media, Person, Category

from vulpes.connections import uses_db

bp = Blueprint('snapcast', __name__, url_prefix='/snapcast')

ADD_TEST_EPISODE = """
    INSERT INTO episode (podcast_id, title, subtitle, episode_uuid, media_url,
                         media_size, media_type, media_duration, pub_date, link)
    VALUES (:podcast_id, :title, :subtitle, :episode_uuid, :media_url, :media_size,
            :media_type, :media_duration, :pub_date, :link)"""
INSERT_EPISODE = """
    INSERT INTO episode (podcast_id, episode_uuid, title, media_url, media_size, media_type, media_duration, pub_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
DELETE_EPISODE_BY_UUID = """DELETE FROM episode WHERE episode_uuid=?"""
SELECT_EPISODE_LATEST = """SELECT * FROM episode ORDER BY id DESC LIMIT 1"""
SELECT_EPISODE_BY_ID = """SELECT * FROM episode WHERE id=?"""
SELECT_EPISODE_BY_UUID = """SELECT * FROM episode WHERE episode_uuid=?"""
SELECT_PODCAST_EPISODES = """SELECT * FROM episode WHERE podcast_id=(SELECT id FROM podcast WHERE feed_id=? limit 1)"""


def authorization_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if request.args.get('passkey') == current_app.config['PODCAST_PUBLISH_AUTH']:
            return func(*args, **kwargs)
        else:
            return abort(401)
    return inner


@bp.route("/<feed_id>/feed.xml")
@uses_db
def generate_feed(db, feed_id):
    res = db.execute("SELECT * FROM podcast WHERE feed_id=?", (feed_id,))
    cast = res.fetchone()
    p = Podcast(
        name=cast['name'],
        description=cast['description'],
        website=cast['website'],
        category=Category(cast['category']),
        language="en-US",
        explicit=cast['explicit'],
        image=cast['image'],
        authors=[Person(name=cast['author_name'])],
        withhold_from_itunes=bool(cast['withhold_from_itunes'])
    )

    res = db.execute("SELECT * FROM episode WHERE podcast_id=?", (cast['id'],))
    episodes = res.fetchall()
    for episode in episodes:
        if media_duration := episode['media_duration']:
            media_duration = timedelta(seconds=media_duration)

        e = Episode(
            id=episode['episode_uuid'],
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

    return Response(p.rss_str(), mimetype='text/xml')


@bp.route("/snapcast.xml")
def generate_snapcast():
    """legacyyyyy"""
    return generate_feed('1787bd99-9d00-48c3-b763-5837f8652bd9')


@bp.route("/snapcast/add_test")
@uses_db
def snapcast_test(db):
    data = {
        "podcast_id": 1,
        "title": "Test Episode3",
        "episode_uuid": str(uuid4()),
        "media_url": "https://f005.backblazeb2.com/file/jbc-external/test_episode_2.mp3",
        "media_size": 9817898,
        "media_type": "audio/mpeg",
        "media_duration": timedelta(seconds=242).total_seconds(),
        "pub_date": datetime.now(timezone.utc)
    }
    db.execute(ADD_TEST_EPISODE, data)
    db.commit()
    return "ok."


@bp.route("/<podcast_id>/publish_episode", methods=["POST"])
@authorization_required
@uses_db
def publish_episode(db, podcast_id):
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
        "podcast_id":       podcast_id,
        "title":            json.get('title', "Untitled Episode"),
        "subtitle":         json.get('subtitle'),

        "episode_uuid":     str(uuid4()),
        "media_url":        json['url'],
        "media_size":       json['size'],
        "media_type":       json['ftype'],
        "media_duration":   json.get('duration'),

        "link":             json.get('link'),
        "pub_date":         pub_date,
    }

    db.execute(ADD_TEST_EPISODE, data).connection.commit()
    return jsonify(success=True)


@bp.route("/episode/<episode_id>", methods=["GET"])
@uses_db
def get_episode(db, episode_id):
    """
    Fetches details of a specific episode. Either an integer episode number,
    a UUID, or -1 which returns the latest episode.
    """
    try:
        episode_id = int(episode_id)
        if episode_id == -1:  # Special case: get the latest episode
            result = db.execute(SELECT_EPISODE_LATEST).fetchone()
        else:
            result = db.execute(SELECT_EPISODE_BY_ID, (episode_id,)).fetchone()
    except ValueError:  # Not integer-y, so a UUID.
        result = db.execute(SELECT_EPISODE_BY_UUID, (episode_id,)).fetchone()

    if result is None:
        return abort(404)
    else:
        return jsonify(dict(result))


@bp.route("/episode/<episode_uuid>", methods=["PATCH"])
@authorization_required
@uses_db
def patch_episode(db, episode_uuid):
    """Just give it a dict with key=rowname value=newvalue. let's get naïve"""
    json = request.json

    rows = 0
    for key in json.keys():
        result = db.execute(f"UPDATE episode SET {key}=? WHERE episode_uuid=?",
                            (json[key], episode_uuid))
        rows += result.rowcount
    db.commit()

    return jsonify(success=True, rows=rows)


@bp.route("/episode/<episode_uuid>", methods=["DELETE"])
@authorization_required
@uses_db
def delete_episode(db, episode_uuid):
    result = db.execute(DELETE_EPISODE_BY_UUID, (episode_uuid,))
    db.commit()

    if result.rowcount == 0:
        return abort(404)
    else:
        return jsonify(success=True)


@bp.route("/podcast/<podcast_uuid>/episodes", methods=["GET"])
@authorization_required
@uses_db
def get_all_episodes(db, podcast_uuid):
    results = db.execute(SELECT_PODCAST_EPISODES, (podcast_uuid,))

    return jsonify([dict(row) for row in results.fetchall()])
