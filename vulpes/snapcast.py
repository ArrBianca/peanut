from flask import Blueprint, Response, request, jsonify, current_app, abort
from podgen import Podcast, Episode, Media, Person
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from vulpes.connections import get_db

bp = Blueprint('snapcast', __name__, url_prefix='/snapcast')


@bp.route("/snapcast.xml")
def generate_snapcast():
    db = get_db()
    cast = db.execute("SELECT * FROM podcast WHERE id=1").fetchone()

    p = Podcast(
        name=cast['name'],
        description=cast['description'],
        website=cast['website'],
        explicit=cast['explicit'],
        image=cast['image'],
        withhold_from_itunes=True
    )
    p.authors = [Person("by June!", "june@peanut.one")]

    eps = db.execute("SELECT * FROM episode WHERE podcast_id=1").fetchall()
    for episode in eps:
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
                duration=timedelta(seconds=episode['media_duration']),
            ),
            publication_date=datetime.fromisoformat(episode['pub_date']),
        )
        p.add_episode(e)

    return Response(p.rss_str(), mimetype='text/xml')


@bp.route("/snapcast/add_test")
def snapcast_test():
    db = get_db()
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
    db.execute("INSERT INTO episode (podcast_id, title, episode_uuid, media_url, media_size, media_type, media_duration, pub_date) VALUES"
               " (:podcast_id, :title, :episode_uuid, :media_url, :media_size, :media_type, :media_duration, :pub_date)", data)
    db.commit()
    return "ok."


@bp.route("/<podcast_id>/publish_episode", methods=["POST"])
def snapcast_add_1(podcast_id):
    if request.args.get('passkey') != current_app.config['PODCAST_PUBLISH_AUTH']:
        return abort(401)

    query = "INSERT INTO episode (podcast_id, episode_uuid, title, media_url, media_size, media_type, media_duration, pub_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    db = get_db()

    # needs title, url, size (bytes), type (mime), duration (seconds) all in the url
    url, size, ftype, duration = [request.args.get(k, type=t) for k, t in
                                  zip("url size type duration".split(), (str, int) * 2)]
    title = request.args.get('title')
    if title is None:
        title = "Untitled"

    data = [podcast_id, str(uuid4()), title, url, size, ftype, duration, datetime.now(timezone.utc)]
    db.execute(query, data).connection.commit()
    return jsonify(success=True)
