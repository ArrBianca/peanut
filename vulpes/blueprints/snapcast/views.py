from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import podgen
from flask import Blueprint, Response, abort, jsonify, request
from sqlalchemy import delete, select, update

from .models import Episode, Podcast
from .util import authorization_required, touch_podcast
from ... import db

bp = Blueprint('snapcast', __name__, url_prefix='/snapcast')


@bp.route("/<uuid:podcast_uuid>/feed.xml", methods=["GET"])
def generate_feed(podcast_uuid: UUID):
    """Pull podcast and episode data from the db and generate a podcast xml file."""
    cast: Podcast = db.first_or_404(
        select(Podcast)
        .where(Podcast.uuid == podcast_uuid),
    )
    print(cast.categories)
    for cat in cast.categories:
        print(repr(cat.__dict__))

    # The caveat to sqlalchemy and sqlite: It stores datetimes as naive.
    last_modified: datetime = cast.last_modified.replace(tzinfo=timezone.utc)
    # The database column stores microseconds which aren't included in the
    # request. If they're just about equal we don't update anything.
    if ((request.if_modified_since is not None) and
       (last_modified - request.if_modified_since).total_seconds() < 1):
        return Response(status=304)

    p = podgen.Podcast(
        name=cast.name,
        description=cast.description,
        website=cast.website,
        category=podgen.Category(cast.categories[0].cat, cast.categories[0].sub),
        language=cast.language,
        explicit=cast.explicit,
        image=cast.image,
        authors=[podgen.Person(name=cast.author_name)],
        withhold_from_itunes=bool(cast.withhold_from_itunes),
        last_updated=last_modified,
    )
    # Assign categories by looping through podcast.categories, as it could be
    # empy

    for episode in cast.episodes:
        e = podgen.Episode(
            id=str(episode.uuid),
            title=episode.title,
            summary=episode.summary,
            subtitle=episode.subtitle,
            long_summary=episode.long_summary,
            media=podgen.Media(
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
    last_modified: Podcast = db.one_or_404(
        select(Podcast.last_modified)
        .where(Podcast.uuid == podcast_uuid),
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

    db.session.add(Episode(**data))
    touch_podcast(podcast_uuid)
    db.session.commit()
    return jsonify(success=True)


@bp.route("/<uuid:podcast_uuid>/episode/<episode_id>", methods=["GET"])
def get_episode(podcast_uuid: UUID, episode_id: str):
    """Fetch details of a specific episode.

    Either an integer episode number,a UUID, or `-1` which returns the latest
    episode.
    """
    try:
        episode_id = int(episode_id)
        if episode_id == -1:  # Special case: get the latest episode
            result: Episode = db.first_or_404(
                select(Episode)
                .order_by(Episode.pub_date.desc()),
            )
        else:
            result: Episode = db.first_or_404(
                select(Episode)
                .where(Episode.podcast_uuid == podcast_uuid)
                .where(Episode.id == episode_id),
            )
    except ValueError:  # Not integer-y, so a UUID probably.
        result: Episode = db.first_or_404(
            select(Episode)
            .where(Episode.podcast_uuid == podcast_uuid)
            .where(Episode.uuid == UUID(episode_id)),
        )

    if result is None:
        return abort(404)
    return jsonify(result.as_dict())


@bp.route("/<uuid:podcast_uuid>/episode/<uuid:episode_uuid>", methods=["PATCH"])
@authorization_required
def patch_episode(podcast_uuid: UUID, episode_uuid: UUID):
    """Just give it a dict with key=rowname value=newvalue. let's get naïve."""
    json = request.json

    if 'media_duration' in json:
        json['media_duration'] = timedelta(seconds=json['media_duration'])
    if 'pub_date' in json:
        json['pub_date'] = datetime.fromisoformat(json['pub_date'])

    result = db.session.execute(
        update(Episode)
        .where(Episode.uuid == episode_uuid)
        .values(json),
    )
    touch_podcast(podcast_uuid)
    db.session.commit()

    return jsonify(success=True, rows=result.rowcount)


@bp.route("/<uuid:podcast_uuid>/episode/<uuid:episode_uuid>", methods=["DELETE"])
@authorization_required
def delete_episode(podcast_uuid: UUID, episode_uuid: UUID):
    """Delete an episode."""
    result = db.session.execute(
        delete(Episode)
        .where(Episode.uuid == episode_uuid)
        .where(Episode.podcast_uuid == podcast_uuid),
    )
    touch_podcast(podcast_uuid)
    db.session.commit()

    if result.rowcount == 0:
        return abort(404)
    return jsonify(success=True)


@bp.route("/<uuid:podcast_uuid>/episodes", methods=["GET"])
@authorization_required
def get_all_episodes(podcast_uuid: UUID):
    """Get all episodes for a podcast."""
    results = db.session.scalars(
        select(Episode)
        .where(Episode.podcast_uuid == podcast_uuid),
    )

    return jsonify([episode.as_dict() for episode in results])
