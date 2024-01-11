from datetime import datetime, timedelta
from uuid import UUID

from flask import abort, jsonify, request
from sqlalchemy import delete, select, update

from ... import db
from . import bp
from .decorators import authorization_required
from .models import Episode
from .sql import touch_podcast


@bp.route("/<uuid:podcast_uuid>/episode/<episode_id>", methods=["GET"])
def get_episode(podcast_uuid: UUID, episode_id: str):
    """Fetch details of a specific episode.

    Either an integer episode number,a UUID, or `-1` which returns the latest
    episode.
    """
    try:
        episode_id = int(episode_id)
        if episode_id == -1:  # Special case: get the latest episode
            result = db.first_or_404(
                select(Episode)
                .order_by(Episode.pub_date.desc()),
            )
        else:
            result = db.first_or_404(
                select(Episode)
                .where(Episode.podcast_uuid == podcast_uuid)
                .where(Episode.id == episode_id),
            )
    except ValueError:  # Not integer-y, so a UUID probably.
        result = db.first_or_404(
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
