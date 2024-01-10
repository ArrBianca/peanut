from datetime import datetime, timedelta, timezone
from uuid import UUID
from uuid import uuid4

from flask import request, Response, jsonify
from flask_sqlalchemy import SQLAlchemy
from podgen import Podcast, Episode, Media, Person, Category
from sqlalchemy import select

from . import bp
from .decorators import authorization_required
from ... import magus
from ...connections import uses_db


@bp.route("/<uuid:podcast_uuid>/feed.xml", methods=["GET"])
@uses_db
def generate_feed(db: SQLAlchemy, podcast_uuid: UUID):
    cast = db.first_or_404(
        select(magus.Podcast)
        .where(magus.Podcast.uuid == podcast_uuid)
    )
    # cast = db.execute(SELECT_PODCAST_BY_UUID, (podcast_uuid,)).fetchone()

    # The caveat to sqlalchemy and sqlite: It stores datetimes as naive
    last_modified: datetime = cast['last_modified'].replace(tzinfo=timezone.utc)
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

    episodes = db.session.execute(
        select(magus.Episode)
        .where(magus.Episode.podcast_uuid == podcast_uuid)
    )
    # episodes = res.fetchall()
    for episode in episodes:
        episode: magus.Episode = episode[0]

        pub_date = episode.pub_date.replace(tzinfo=timezone.utc)

        e = Episode(
            id=str(episode.uuid),
            title=episode['title'],
            summary=episode['summary'],
            subtitle=episode['subtitle'],
            long_summary=episode['long_summary'],
            media=Media(
                episode['media_url'],
                size=episode['media_size'],
                type=episode['media_type'],
                duration=episode.media_duration,
            ),
            publication_date=pub_date,
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
    last_modified = db.one_or_404(
        select(magus.Podcast.last_modified)
        .where(magus.Podcast.uuid == podcast_uuid)
    )
    response = Response()
    response.last_modified = last_modified.replace(tzinfo=timezone.utc)
    return response


@bp.route("/snapcast.xml")
def generate_snapcast():
    """shortcut!"""
    if request.method == "HEAD":
        return feed_head(UUID("1787bd99-9d00-48c3-b763-5837f8652bd9"))
    else:
        return generate_feed(UUID("1787bd99-9d00-48c3-b763-5837f8652bd9"))


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

    db.session.add(magus.Episode(**data))
    # db.execute(ADD_EPISODE, data)
    # db.execute(
    #     "UPDATE podcast SET last_modified = ? WHERE uuid = ?",
    #     (datetime.now(timezone.utc), podcast_uuid)
    # )
    # db.commit()
    return jsonify(success=True)
