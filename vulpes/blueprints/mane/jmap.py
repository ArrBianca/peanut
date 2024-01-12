from functools import wraps
from json import dumps

from flask import current_app, g
from requests import get, post


class JMAPClient:
    """The J stands for June!"""  # noqa: D400 smh

    def __init__(self, hostname, username, token):
        self.hostname = hostname
        self.username = username
        self.token = token
        self._session = None
        self._account_id = None
        # You need an Identity to send mail. _apparently_
        self._identity_id = None
        self._upload_url = None

    @property
    def session(self):
        """The JMAP session for the current user."""
        if self._session is not None:
            return self._session
        r = get(
            "https://" + self.hostname + "/.well-known/jmap",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
        )
        r.raise_for_status()
        self._session = r.json()
        return self._session

    @property
    def account_id(self):
        """The accountId for the account matching self.username."""
        if self._account_id:
            return self._account_id

        account_id = self.session["primaryAccounts"]["urn:ietf:params:jmap:mail"]
        self._account_id = account_id
        return self._account_id

    @property
    def api_url(self):
        """The root API URL for the server."""
        return self.session['apiUrl']

    @property
    def upload_url(self):
        """The account's upload url for attachments."""
        if self._upload_url:
            return self._upload_url

        upload_url = self.session["uploadUrl"].replace("{accountId}", self.account_id)
        self._upload_url = upload_url
        return self._upload_url

    @property
    def identity_id(self):
        """The identityId for an address matching self.username."""
        if self._identity_id:
            return self._identity_id

        ident_result = self.jmap_call({
            "using": ["urn:ietf:params:jmap:submission"],
            "methodCalls": [
                ["Identity/get",
                    {"accountId": self.account_id},
                 'i'],
            ],
        })

        identity_id = next(
            filter(
                lambda i: i["email"] == self.username,
                ident_result["methodResponses"][0][1]["list"],
            ),
        )["id"]

        self._identity_id = str(identity_id)
        return self._identity_id

    # @cache
    def mailbox_by_name(self, name: str) -> str:
        """Retrieve the ID of the first mailbox matching the given name."""
        response = self.jmap_call({
            'using': ["urn:ietf:params:jmap:mail"],
            'methodCalls': [
                ["Mailbox/query",
                    {"accountId": self.account_id,
                        "filter": {"name": name},
                     },
                 "a"],
            ],
        })
        # Responses -> Response for Call #0 -> resp[1] is the result dict ->
        #   list of matching ids -> First one
        return response['methodResponses'][0][1]['ids'][0]

    def prepare_plaintext_email(self, to_addr: str,
                                subject: str, body: str) -> dict:
        """Prepare a dictionary containing the required fields to send aplaintext email message."""
        return {
            "from": [{"email": self.username}],
            "to": [{"email": to_addr}],
            "subject": subject,
            "keywords": {"$draft": True},
            "mailboxIds": {self.mailbox_by_name("Drafts"): True},
            "bodyValues": {"body": {"value": body, "charset": "utf-8"}},
            # If given, textBody MUST contain exactly one body part and it
            # MUST be of type text/plain.
            "textBody": [{"partId": "body", "type": "text/plain"}],
        }

    def attach_file_to_message(self, draft: dict,
                               file_data: bytes, filename: str) -> None:
        """Upload an attachment and append its date to the message draft."""
        uploaded = self.file_upload(file_data)
        if 'attachments' not in draft:
            draft['attachments'] = []
        draft["attachments"].append({
            "blobId": uploaded["blobId"],
            "type": uploaded["type"],
            "name": filename,
        })

    def send(self, message: dict) -> dict:
        """Send an email."""
        return self.jmap_call({
            "using": ["urn:ietf:params:jmap:core",
                      "urn:ietf:params:jmap:mail",
                      "urn:ietf:params:jmap:submission"],
            "methodCalls": [
                ["Email/set",
                    {"accountId": self.account_id,
                        "create": {"draft": message},
                     },
                 "a"],
                ["EmailSubmission/set",
                    {"accountId": self.account_id,
                        "create": {
                            "sendIt": {
                                "emailId": "#draft",
                                "identityId": self.identity_id,
                            },
                        },
                        "onSuccessDestroyEmail": ["#sendIt"],
                     },
                 "b"],
            ],
        })

    def jmap_call(self, call: dict) -> dict:
        """Make a JMAP POST request to the API, return the response as a Python data structure."""
        return self._api_call(self.api_url, dumps(call))

    def file_upload(self, file_data: bytes) -> dict:
        """Upload file date to the out-of-band upload endpoint.

        Returns a response what looks like this:

            {'accountId': str,
        'blobId': str,
        'expires': iso-date,
        'size': int,
        'type': str}
        """
        return self._api_call(self.upload_url, file_data)

    def _api_call(self, endpoint: str, data: str | bytes) -> dict:
        res = post(
            endpoint,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
            data=data,
        )
        res.raise_for_status()
        return res.json()


def get_jmap():
    """Create or return the configured JMAPClient."""
    if 'jmap' not in g:
        g.jmap = JMAPClient(
            current_app.config['JMAP']['HOSTNAME'],
            current_app.config['JMAP']['USERNAME'],
            current_app.config['JMAP']['TOKEN'],
        )

    return g.jmap


def uses_jmap(func):
    """Wrap a function that needs to use JMAP."""

    @wraps(func)
    def inner(*args, **kwargs):
        client = get_jmap()
        return func(client, *args, **kwargs)

    return inner
