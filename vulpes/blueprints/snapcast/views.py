from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from flask import Response, jsonify, request
from podgen import Category, Episode, Media, Person, Podcast
from sqlalchemy import select

from ... import db
from . import bp, models
from .decorators import authorization_required
from .sql import touch_podcast


@bp.route("/<uuid:podcast_uuid>/feed.xml", methods=["GET"])
def generate_feed(podcast_uuid: UUID):
    """Pull podcast and episode data from the db and generate a podcast xml file."""
    cast: models.Podcast = db.first_or_404(
        select(models.Podcast)
        .where(models.Podcast.uuid == podcast_uuid),
    )

    # The caveat to sqlalchemy and sqlite: It stores datetimes as naive.
    last_modified: datetime = cast.last_modified.replace(tzinfo=timezone.utc)
    # The database column stores microseconds which aren't included in the
    # request. If they're just about equal we don't update anything.
    if ((request.if_modified_since is not None) and
       (last_modified - request.if_modified_since).total_seconds() < 1):
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

    episodes = db.session.scalars(
        select(models.Episode)
        .where(models.Episode.podcast_uuid == podcast_uuid),
    )
    for episode in episodes:
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
            image=episode.episode_art,
        )
        p.add_episode(e)

    response = Response(p.rss_str(), mimetype='text/xml')
    response.last_modified = last_modified
    return response


@bp.route("/<uuid:podcast_uuid>/feed.xml", methods=["HEAD"])
def feed_head(podcast_uuid: UUID):
    """Set headers for a HEAD request to a feed.

    Fill `Last-Modified` to save on data transfer.
    """
    last_modified = db.one_or_404(
        select(models.Podcast.last_modified)
        .where(models.Podcast.uuid == podcast_uuid),
    )
    response = Response()
    response.last_modified = last_modified.replace(tzinfo=timezone.utc)
    return response


@bp.route("/snapcast.xml")
def generate_snapcast():
    """shortcut!"""
    if request.method == "HEAD":
        return feed_head(UUID("1787bd99-9d00-48c3-b763-5837f8652bd9"))
    return generate_feed(UUID("1787bd99-9d00-48c3-b763-5837f8652bd9"))


@bp.route("/<uuid:podcast_uuid>/publish", methods=["POST"])
@authorization_required
def publish_episode(podcast_uuid: UUID):
    """Add a new episode to a podcast.

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

    db.session.add(models.Episode(**data))
    touch_podcast(podcast_uuid)
    db.session.commit()
    return jsonify(success=True)
