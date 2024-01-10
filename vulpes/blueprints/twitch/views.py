from flask import current_app as app, render_template, jsonify
from requests import get

from . import bp
from .utils import multifind

_prefix = 'https://api.twitch.tv/helix'


@bp.before_app_request
def a():
    """Add the twitch authorization to all the requests made in the views below."""
    app.config['_headers'] = {'Accept': 'application/vnd.twitchtv.v5+json',
                              'Client-ID': app.config['TWITCH_CLIENT_ID'],
                              'Authorization': "Bearer {}".format(app.config['TWITCH_TOKEN'])}


@bp.route("/game/<game>")
def names(game):
    """Display a list of the top streamers for a particular game."""
    res = game_streamers(game)

    streamers = multifind(res, "channel", "display_name")
    viewers = multifind(res, "viewers")
    links = multifind(res, "channel", "name")
    statuses = multifind(res, "channel", "status")

    return render_template("twitch/gamelisting.html",
                           title=game,
                           cols=[streamers, viewers, links],
                           stats=statuses)


@bp.route("/user/<username>")
def following(username):
    """Display a list of all active streams from a user's following list."""
    res = followed_streams(username)

    streamers = multifind(res, "user_name")
    games = multifind(res, "game_name")
    viewers = multifind(res, "viewer_count")
    links = multifind(res, "user_login")
    statuses = multifind(res, "title")

    return render_template("twitch/followinglisting.html",
                           title=username,
                           cols=[streamers, games, viewers, links],
                           stats=statuses)


@bp.route("/user/<username>/simple")
def userbot(username):
    """Return the same data as above, but as a JSON object for automated parsing."""
    res = followed_streams(username)

    streamers = multifind(res, "user_name")
    games = multifind(res, "game_name")
    viewers = multifind(res, "viewer_count")

    logos = [streamer_logo(s) for s in streamers]

    resp = list()
    for streamer, game, viewer, logo in zip(streamers, games, viewers, logos):
        resp.append(
            {
                'streamer': streamer,
                'game': game,
                'viewers': viewer,
                'logo': logo
            }
        )

    return jsonify(resp)


def streamer_logo(streamer):
    """Get the profile picture of a streamer."""
    return get("{}/users".format(_prefix),
               params={'login': streamer},
               headers=app.config['_headers']).json()['data'][0]['profile_image_url']


def followed_streams(name):
    """Get the stream info for live channels followed by the given user."""
    resp = get("{}/users".format(_prefix),
               params={'login': name},
               headers=app.config['_headers']).json()

    my_uid = resp['data'][0]['id']

    h = app.config['_headers']
    h['Authorization'] = "Bearer {}".format(app.config['TWITCH_USER_TOKEN'])
    resp = get("{}/channels/followed".format(_prefix),
               params={'user_id': my_uid, 'first': 100},
               headers=h)

    streamer_uids = [c['broadcaster_id'] for c in resp.json()['data']]

    resp = get('{}/streams'.format(_prefix),
               params={'user_id': streamer_uids},
               headers=app.config['_headers'])

    return resp.json()['data']


def game_streamers(game: str):
    """Get the 15 highest viewcount streams of a given game."""
    resp = get("{}/streams".format(_prefix),
               params={'game': game, 'limit': 15},
               headers=app.config['_headers'])

    return resp.json()['streams']
