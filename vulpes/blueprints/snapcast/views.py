from datetime import datetime, timezone, timedelta
from uuid import UUID
from uuid import uuid4

from flask import request, Response, jsonify
from flask_sqlalchemy import SQLAlchemy
from podgen import Podcast, Episode, Media, Person, Category
from sqlalchemy import select

from . import bp
from .decorators import authorization_required
from .sql import touch_podcast
from ... import nitre
from ...connections import uses_db


@bp.route("/<uuid:podcast_uuid>/feed.xml", methods=["GET"])
@uses_db
def generate_feed(db: SQLAlchemy, podcast_uuid: UUID):
    cast: magus.Podcast = db.first_or_404(
        select(magus.Podcast)
        .where(magus.Podcast.uuid == podcast_uuid)
    )

    # The caveat to sqlalchemy and sqlite: It stores datetimes as naive.
    last_modified: datetime = cast['last_modified'].replace(tzinfo=timezone.utc)
    if since := request.if_modified_since:
        # The database column stores microseconds which aren't included in the
        # request. If they're just about equal we don't update anything.
        if (last_modified - since).total_seconds() < 1:
            return Response(status=304)

    p = Podcast(
        name=cast.name,
        description=cast.description,
        website=cast.website,
        category=Category(cast.category),
        language=cast.language,
        explicit=cast.explicit,
        image=cast.image,
        authors=[Person(name=cast.author_name)],
        withhold_from_itunes=bool(cast.withhold_from_itunes),
        last_updated=last_modified,
    )

    episodes = db.session.execute(
        select(magus.Episode)
        .where(magus.Episode.podcast_uuid == podcast_uuid)
    )
    for episode in episodes:
        # Row object is a 2-tuple with the object in [0]. idk why.
        episode: magus.Episode = episode[0]

        e = Episode(
            id=str(episode.uuid),
            title=episode.title,
            summary=episode.summary,
            subtitle=episode.subtitle,
            long_summary=episode.long_summary,
            media=Media(
                episode.media_url,
                size=episode.media_size,
                type=episode.media_type,
                duration=episode.media_duration,
            ),
            publication_date=episode.pub_date.replace(tzinfo=timezone.utc),
            link=episode.link,
            image=episode.episode_art
        )
        p.add_episode(e)

    response = Response(p.rss_str(), mimetype='text/xml')
    response.last_modified = last_modified
    return response


@bp.route("/<uuid:podcast_uuid>/feed.xml", methods=["HEAD"])
@uses_db
def feed_head(db: SQLAlchemy, podcast_uuid: UUID):
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


@bp.route("/<uuid:podcast_uuid>/publish", methods=["POST"])
@uses_db
@authorization_required
def publish_episode(db: SQLAlchemy, podcast_uuid: UUID):
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

        "uuid":             uuid4(),
        "media_url":        json['url'],
        "media_size":       json['size'],
        "media_type":       json['ftype'],
        "media_duration":   timedelta(seconds=json.get('duration')),

        "link":             json.get('link'),
        "pub_date":         pub_date,
    }

    db.session.add(magus.Episode(**data))
    touch_podcast(db, podcast_uuid)
    db.session.commit()
    return jsonify(success=True)
