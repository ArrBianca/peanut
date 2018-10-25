import requests
from flask import abort
from flask import current_app as app

_prefix = 'https://api.twitch.tv/kraken'


def followed_streams(name):
    resp = requests.get("{}/users".format(_prefix),
                        params={'login': name},
                        headers=app.config['_headers']).json()

    if resp['_total'] == 0: abort(400)  # Invalid username
    my_uid = resp['users'][0]['_id']

    resp = requests.get("{}/users/{}/follows/channels".format(_prefix, my_uid),
                        params={'limit': '100'},
                        headers=app.config['_headers'])

    streamer_uids = [c['channel']['_id'] for c in resp.json()['follows']]

    resp = requests.get('{}/streams'.format(_prefix),
                        params={'channel': ','.join(streamer_uids)},
                        headers=app.config['_headers'])

    #print(resp.json()['streams'])
    return resp.json()['streams']


def game_streamers(game):
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
