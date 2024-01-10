from datetime import datetime, timezone
from uuid import UUID

from flask import abort, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select, update, delete

from . import bp
from .sql import touch_podcast
from .decorators import authorization_required
from ...connections import uses_db
from ...magus import Episode, Podcast


@bp.route("/<uuid:podcast_uuid>/episode/<episode_id>", methods=["GET"])
@uses_db
def get_episode(db: SQLAlchemy, podcast_uuid: UUID, episode_id):
    """Fetches details of a specific episode.

    Either an integer episode number,a UUID, or `-1` which returns the latest
    episode.
    """
    print(podcast_uuid, episode_id)
    try:
        episode_id = int(episode_id)
        if episode_id == -1:  # Special case: get the latest episode
            result = db.first_or_404(
                select(Episode)
                .order_by(Episode.pub_date.desc())
            )
        else:
            result = db.first_or_404(
                select(Episode)
                .where(Episode.podcast_uuid == podcast_uuid)
                .where(Episode.rowid == episode_id)
            )
    except ValueError:  # Not integer-y, so a UUID probably.
        result = db.first_or_404(
            select(Episode)
            .where(Episode.podcast_uuid == podcast_uuid)
            .where(Episode.uuid == UUID(episode_id))
        )

    if result is None:
        return abort(404)
    else:
        return jsonify(result.as_dict())


@bp.route("/<uuid:podcast_uuid>/episode/<uuid:episode_uuid>", methods=["PATCH"])
@uses_db
@authorization_required
def patch_episode(db: SQLAlchemy, podcast_uuid, episode_uuid):
    """Just give it a dict with key=rowname value=newvalue. let's get naïve"""
    json = request.json

    result = db.session.execute(
        update(Episode)
        .where(Episode.uuid == episode_uuid)
        .values(json)
    )
    touch_podcast(db, podcast_uuid)
    db.session.commit()

    return jsonify(success=True, rows=result.rowcount)


@bp.route("/<uuid:podcast_uuid>/episode/<uuid:episode_uuid>", methods=["DELETE"])
@uses_db
@authorization_required
def delete_episode(db: SQLAlchemy, podcast_uuid: UUID, episode_uuid: UUID):
    result = db.session.execute(
        delete(Episode)
        .where(Episode.uuid == episode_uuid)
        .where(Episode.podcast_uuid == podcast_uuid)
    )
    touch_podcast(db, podcast_uuid)
    db.commit()

    if result.rowcount == 0:
        return abort(404)
    else:
        return jsonify(success=True)


@bp.route("/<podcast_uuid>/episodes", methods=["GET"])
@uses_db
@authorization_required
def get_all_episodes(db: SQLAlchemy, podcast_uuid):
    results = db.session.execute(
        select(Episode)
        .where(Episode.podcast_uuid == UUID(podcast_uuid))
    )

    return jsonify([row._mapping.as_dict() for row in results])
