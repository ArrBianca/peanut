def jsonfind(json, *args):
    """Traverse a JSON object by a set of named keys.

    jsonfind(j, "foo", "bar") ->
        j["foo"]["bar"], but returns None on failure.

    Knowing what I know now I'd do this way differently lol.
    """
    for arg in args:
        if arg in json:
            json = json[arg]
        else:
            return None
    return json


def multifind(jsonlist, *args):
    """Given a list of JSON objects, traverse each in an identical way and return results."""
    return [jsonfind(json, *args) for json in jsonlist]
