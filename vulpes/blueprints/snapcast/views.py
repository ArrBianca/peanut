from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from flask import Blueprint, Response, abort, request
from sqlalchemy import delete, select, update
from sqlalchemy.orm import joinedload

from .jvalidate import (
    Pull,
    episode_type,
    image,
    media_type,
    non_negative,
    positive,
    to_datetime,
    to_timedelta,
    url,
)
from .jxml import mime_lookup
from .models import Episode, Podcast
from .util import authorization_required, touch_podcast
from ... import db

bp = Blueprint("snapcast", __name__, url_prefix="/snapcast")


@bp.route("/<uuid:podcast_uuid>/feed.xml", methods=["GET"])
def generate_feed(podcast_uuid: UUID):
    """Pull podcast and episode data from the db and generate podcast xml."""
    # noinspection PyTypeChecker
    cast: Podcast = db.first_or_404(
        select(Podcast)
        .where(Podcast.uuid == podcast_uuid)
        .options(joinedload("*")),
    )

    if ((request.if_modified_since is not None) and
       (cast.last_build_date <= request.if_modified_since)):
        return Response(status=304)

    response = Response(cast.build(pretty=True), mimetype="text/xml")
    response.last_modified = cast.last_build_date
    return response


@bp.route("/<uuid:podcast_uuid>/feed.xml", methods=["HEAD"])
def feed_head(podcast_uuid: UUID):
    """Set headers for a HEAD request to a feed.

    Fill `Last-Modified` to save on data transfer.
    """
    last_modified: datetime = db.one_or_404(
        select(Podcast.last_build_date)
        .where(Podcast.uuid == podcast_uuid),
    )
    response = Response()
    response.last_modified = last_modified
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
        title:        str,
        url:          str, media_url
        size:         int, media_size
    Optional elements:
        subtitle:     str,
        description:  str,
        duration:     int, media_duration
        timestamp:    int, pub_date
        link:         str,
        image:        str,
        episode_type: str,
        season:       int,
        episode:      int,

    media_type is set automatically.
    """
    json = request.json
    if json is None:
        return {}

    # The structure of this should mimic that of the input dict.
    extractors = (
        Pull("title", required=True),
        Pull("subtitle"),
        Pull("description"),
        Pull(
            "timestamp",
            to_datetime,
            to="pub_date",
            default=datetime.now(timezone.utc),
        ),

        Pull("url", url, media_type, to="media_url", required=True),
        Pull("size", non_negative, to="media_size", required=True),
        Pull("duration", non_negative, to_timedelta, to="media_duration"),

        Pull("link", url),
        Pull("image", url, image),

        Pull("episode_type", episode_type),
        Pull("episode", positive),
        Pull("season", positive),
    )
    data = {}
    for extractor in extractors:
        try:
            # Typeerror if a filter fails.
            # ValueError if it's required and missing.
            data[extractor.to] = extractor.run(json)
        except ValueError as e:
            abort(400, description=e.__str__())
        except TypeError as e:
            abort(422, description=e.__str__())

    # Right now data has the stuff from the JSON, now we add the extra
    # data needed for the db.
    data["uuid"] = uuid4()
    data["podcast_uuid"] = podcast_uuid
    data["media_type"] = mime_lookup[data["media_url"][-4:]]

    db.session.add(Episode(**data))
    touch_podcast(podcast_uuid)
    db.session.commit()
    return {}


@bp.route("/<uuid:podcast_uuid>/episode/<episode_id>", methods=["GET"])
def get_episode(podcast_uuid: UUID, episode_id: str):
    """Fetch details of a specific episode.

    Either an integer episode number,a UUID, or `-1` which returns the latest
    episode.
    """
    try:
        id_number = int(episode_id)
        if id_number == -1:  # Special case: get the latest episode
            result: Episode = db.first_or_404(
                select(Episode)
                .where(Episode.podcast_uuid == podcast_uuid)
                .order_by(Episode.pub_date.desc()),
            )
        else:
            result: Episode = db.first_or_404(
                select(Episode)
                .where(Episode.podcast_uuid == podcast_uuid)
                .where(Episode.id == episode_id),
            )
    except ValueError:  # Not integer-y, so a UUID. Probably.
        result: Episode = db.first_or_404(
            select(Episode)
            .where(Episode.podcast_uuid == podcast_uuid)
            .where(Episode.uuid == UUID(episode_id)),
        )

    return result.as_dict()


@bp.route("/<uuid:podcast_uuid>/episode/<uuid:episode_uuid>",
          methods=["PATCH"])
@authorization_required
def patch_episode(podcast_uuid: UUID, episode_uuid: UUID):
    """Just give it a dict with key=rowname value=newvalue. let's get naïve."""
    json = request.json
    if json is None:
        abort(400)

    if "media_duration" in json:
        json["media_duration"] = timedelta(seconds=json["media_duration"])
    if "pub_date" in json:
        json["pub_date"] = datetime.fromisoformat(json["pub_date"])

    result = db.session.execute(
        update(Episode)
        .where(Episode.uuid == episode_uuid)
        .values(json),
    )
    touch_podcast(podcast_uuid)
    db.session.commit()

    return {"rows": result.rowcount}


@bp.route("/<uuid:podcast_uuid>/episode/<uuid:episode_uuid>",
          methods=["DELETE"])
@authorization_required
def delete_episode(podcast_uuid: UUID, episode_uuid: UUID):
    """Delete an episode."""
    result = db.session.execute(
        delete(Episode)
        .where(Episode.uuid == episode_uuid)
        .where(Episode.podcast_uuid == podcast_uuid),
    )

    if result.rowcount == 0:
        return abort(404)
    touch_podcast(podcast_uuid)
    db.session.commit()

    return {}


@bp.route("/<uuid:podcast_uuid>/episodes", methods=["GET"])
@authorization_required
def get_all_episodes(podcast_uuid: UUID):
    """Get all episodes for a podcast."""
    results = db.session.scalars(
        select(Episode)
        .where(Episode.podcast_uuid == podcast_uuid),
    )

    return [episode.as_dict() for episode in results]
