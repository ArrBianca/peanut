def jsonfind(json, *args):
    for arg in args:
        if arg in json:
            json = json[arg]
        else:
            return None
    return json


def multifind(jsonlist, *args):
    return [jsonfind(json, *args) for json in jsonlist]
