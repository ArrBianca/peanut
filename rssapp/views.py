import requests
from lxml import etree
from . import rssapp
from flask import request
# import oauth2

# KEY = "hh9kvKSkT4fMz4O2Hrvf8fDVu"
# SECRET = "BliUbPmBA2`8AEF3uagKVpMrDOqIisLJxuxqCJZ62Q2hVUtueHq"

# AUTH = base64.b64encode(b"hh9kvKSkT4fMz4O2Hrvf8fDVu:BliUbPmBA28AEF3uagKVpMrDOqIisLJxuxqCJZ62Q2hVUtueHq")  # noqa: E501

# r = requests.post("https://api.twitter.com/oauth2/token",
# 	headers={"Authorization": b"Basic " + AUTH,
# 			 "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
# 			 "User-Agent": "Sweet Reader Of Mine v0.1"},
# 	data={"grant_type": "client_credentials"})

# print(r.json())
# print(r)
# print(r.text)

# {'token_type': 'bearer', 'access_token': 'AAAAAAAAAAAAAAAAAAAAAIG51QAAAAAA7j1fJ3o5atxmyySszANlimXMZzY%3DA5Nb31GK7IKHe6VXQtUstf7bdZl0YDHrPvOJZoj8Uwn1C2uzMl'}  # noqa: E501

# https://api.twitter.com/1.1/favorites/list.json
# https://api.twitter.com/1.1/statuses/user_timeline.json


def tweet2rss(tweet: dict) -> etree.Element:
    """
    Certain elements in the Tweet will map to rss tags. Others will be
    collected together and formatted into the description tag.

    :tag <title>: Generated from the Tweet data, likely in the form either
        "Tweet from X" or "Retweet from X, Y" maybe
    :tag <link>: A direct link to the tweet probably.
    :tag <description>: The full text of the tweet, followed by any images
        linked, with a line break between them. Note: remember to element
        encode this data so it doesn't break everything. Also probably
        sanitize the tweet just in case.
    :param tweet: the full JSON object of a Tweet
    :return: A full <item> unit for inclusion in an RSS feed
    """
    tweet = locate_root_tweet(tweet)
    tweet_source = tweet['user']['screen_name']
    tweet_link = "http://twitter.com/{}/status/{}".format(
            tweet_source, tweet['id_str'])

    block = etree.Element("item")
    block.append(simple_tag("title", "Tweet from @" + tweet_source))
    block.append(simple_tag("link", tweet_link))
    block.append(simple_tag("pubDate", tweet["created_at"]))
    # description = escape(tweet['full_text'])
    description = tweet['full_text']

    # Embed tweet images, and remove the text link
    if tweet.get('extended_entities') is not None:
        for entry in tweet['extended_entities']['media']:
            description = description.replace(entry['url'], '')
            description += "<br><img src='{0}'>".format(entry['media_url_https'])

    # Linkify links in the tweet
    for url in tweet['entities']['urls']:
        description = description.replace(url['url'], '<a href="{0}">{1}</a>'.format(url['expanded_url'], url['display_url']))  # noqa: E501

    # Linkify hashtags in the tweet
    for hashtag in tweet['entities']['hashtags']:
        description = description.replace(
                '#' + hashtag['text'],
                '<a href="https://twitter.com/hashtag/{0}">#{0}</a>'.format(hashtag['text']))  # noqa: E501

    block.append(simple_tag("description", description))

    return block


def simple_tag(tag, text, **kwargs):
    element = etree.Element(tag, **kwargs)
    element.text = text
    return element


def locate_root_tweet(tweet):
    if tweet.get('retweeted_status') is not None:
        return locate_root_tweet(tweet['retweeted_status'])
    elif tweet.get('quoted_status') is not None:
        return locate_root_tweet(tweet['quoted_status'])
    else:
        return tweet


@rssapp.route("/twitter/<feed>.rss")
def feedify(feed):
    root = etree.Element("rss", version="2.0")
    tree = etree.ElementTree(root)
    # title = etree.Element("title")
    # title.text = "A test RSS feed"
    # root.append(title)

    channel = etree.Element("channel")
    root.append(channel)

    channel.append(simple_tag("title", "@{} Timeline".format(feed)))
    channel.append(simple_tag("link", request.base_url))
    channel.append(simple_tag("description", "Description text goes here"))

    params = {
        "count": 30,
        "screen_name": feed,
        "exclude_replies": "t",
        "tweet_mode": "extended",
        # "include_rts": bool(request.args.get("strip_rts"))
    }

    api_request = requests.get(
                     "https://api.twitter.com/1.1/statuses/user_timeline.json",
                     params=params,
                     headers={
                         "Authorization": b"Bearer AAAAAAAAAAAAAAAAAAAAAIG51QAAAAAA7j1fJ3o5atxmyySszANlimXMZzY%3DA5Nb31GK7IKHe6VXQtUstf7bdZl0YDHrPvOJZoj8Uwn1C2uzMl",  # noqa: E501
                         "User-Agent": "Sweet Reader Of Mine v0.1"
                     })

    json = api_request.json()
    for tweet in json:
        channel.append(tweet2rss(tweet))
    return etree.tostring(tree, xml_declaration=True, encoding="utf8")


@rssapp.route("/github/<user>/<repo>.atom")
def github_translate(user, repo):
    fullname = "{}/{}".format(user, repo)
    feed = "https://github.com/{}/commits/master.atom".format(fullname)
    tree = etree.fromstring(requests.get(feed).content)
    for child in tree.findall('{*}entry'):
        child.find('{*}title').text = "New commmit in " + fullname
        # child.remove(child.find('{*}thumbnail'))
    return etree.tostring(tree)
