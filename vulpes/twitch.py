from flask import Blueprint, render_template, jsonify
from flask import current_app as app
import requests

bp = Blueprint('twitch', __name__, url_prefix="/twitch")
_prefix = 'https://api.twitch.tv/helix'


@bp.before_app_request
def a():
    app.config['_headers'] = {'Accept': 'application/vnd.twitchtv.v5+json',
                              'Client-ID': app.config['TWITCH_CLIENT_ID'],
                              'Authorization': "Bearer {}".format(app.config['TWITCH_TOKEN'])}


@bp.route("/game/<game>")
def names(game):
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
    return requests.get("{}/users".format(_prefix),
                        params={'login': streamer},
                        headers=app.config['_headers']).json()['data'][0]['profile_image_url']


def followed_streams(name):
    resp = requests.get("{}/users".format(_prefix),
                        params={'login': name},
                        headers=app.config['_headers']).json()

    my_uid = resp['data'][0]['id']

    h = app.config['_headers']
    h['Authorization'] = "Bearer {}".format(app.config['TWITCH_USER_TOKEN'])
    resp = requests.get("{}/channels/followed".format(_prefix),
                        params={'user_id': my_uid, 'first': 100},
                        headers=h)

    streamer_uids = [c['broadcaster_id'] for c in resp.json()['data']]

    resp = requests.get('{}/streams'.format(_prefix),
                        params={'user_id': streamer_uids},
                        headers=app.config['_headers'])

    return resp.json()['data']


def game_streamers(game: str):
    resp = requests.get("{}/streams".format(_prefix),
                        params={'game': game, 'limit': 15},
                        headers=app.config['_headers'])

    return resp.json()['streams']


def jsonfind(json, *args):
    for arg in args:
        if arg in json:
            json = json[arg]
        else:
            return None
    return json


def multifind(jsonlist, *args):
    return [jsonfind(json, *args) for json in jsonlist]
