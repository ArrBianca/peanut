from . import twitchapp
from .ttv import multifind, followed_streams, game_streamers
from flask import render_template, jsonify
from flask import current_app as app


@twitchapp.before_app_request
def a():
    app.config['_headers'] = {'Accept': 'application/vnd.twitchtv.v5+json',
            'Client-ID': app.config['TWITCH_CLIENT_ID']}


@twitchapp.route('/')
def hello_world():
    return "Hello, World!"


@twitchapp.route("/game/<game>")
def names(game):
    res = game_streamers(game)

    streamers = multifind(res, "channel", "display_name")
    viewers = multifind(res, "viewers")
    links = multifind(res, "channel", "name")
    statuses = multifind(res, "channel", "status")

    return render_template("gamelisting.html",
                           title=game,
                           cols=[streamers, viewers, links],
                           stats=statuses)


@twitchapp.route("/user/<username>")
def following(username):
    res = followed_streams(username)

    streamers = multifind(res, "channel", "display_name")
    games = multifind(res, "channel", "game")
    viewers = multifind(res, "viewers")
    links = multifind(res, "channel", "name")
    statuses = multifind(res, "channel", "status")

    return render_template("followinglisting.html",
                           title=username,
                           cols=[streamers, games, viewers, links],
                           stats=statuses)


@twitchapp.route("/user/<username>/simple")
def userbot(username):
    res = followed_streams(username)

    streamers = multifind(res, "channel", "display_name")
    games = multifind(res, "channel", "game")
    viewers = multifind(res, "viewers")
    logos = multifind(res, "channel", "logo")

    # ret = ''.join("{}\t{}\t{}\n".format(*i) for i in
    #  zip(streamers, games, viewers))
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
