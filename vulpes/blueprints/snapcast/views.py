from datetime import datetime, timedelta, timezone
from uuid import uuid4

from flask import request, Response, jsonify, abort
from podgen import Podcast, Episode, Media, Person, Category

from . import bp
from .decorators import authorization_required
from .sql import *
from ...connections import uses_db


@bp.route("/<podcast_uuid>/feed.xml", methods=["GET"])
@uses_db
def generate_feed(db, podcast_uuid):
    cast = db.execute(SELECT_PODCAST_BY_UUID, (podcast_uuid,)).fetchone()

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


@bp.route("/<podcast_uuid>/publish", methods=["POST"])
@uses_db
@authorization_required
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
@uses_db
@authorization_required
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
@uses_db
@authorization_required
def get_all_episodes(db, podcast_uuid):
    results = db.execute(SELECT_PODCAST_EPISODES, (podcast_uuid,))

    return jsonify([dict(row) for row in results.fetchall()])
