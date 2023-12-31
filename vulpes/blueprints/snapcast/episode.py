from datetime import datetime, timezone

from flask import abort, jsonify, request

from . import bp
from .decorators import authorization_required
from .sql import *
from ...connections import uses_db


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
