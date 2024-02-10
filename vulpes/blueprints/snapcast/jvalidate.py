"""The J stands for June!"""  # noqa: D400 fite me
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from .jxml import mime_lookup


class Pull:
    """Dict-to-dict value extractor and rule checker."""

    def __init__(
            self,
            from_,
            *rules: Callable,
            required: bool = False,
            to: str | None = None,
            default: Any | None = None,
    ):
        """Set up a value to be pulled from a dict and processed.

        :param from_: The dict field to take the value from.
        :param rules: zero to several callables like the ones below
            that take the value as well as its key name for error
            formatting, and transform or validate the value. Raise a
            TypeError if the value does not pass validation, return
            the value unaltered if no changes are made.
        :param required: whether processhing should abort on a missing,
            defaultless value.
        :param to: the name of the key in the result dict. If left as
            None, `from_` is used.
        :param default: A default value to use if the key is not present
            in the source. Overrules `required` if set.
        """
        self.from_ = from_
        self.rules = rules
        self.required = required
        self.to = to or from_
        self.default = default

    def run(self, source: dict) -> Optional[dict[str, Any]]:
        """Pull the value.

        Grab a specified value from a dictionary, apply a chain of callables
        for conversion and validation, and return a key-value pair.
        """
        value = source.get(self.from_)
        if value is None:
            if self.default is not None:
                return self.default
            if self.required:
                raise ValueError(f"{self.from_} missing.")
            return None
        for rule in self.rules:
            value = rule(value, field=self.from_)

        return value


def url(value: str, field: str):  # noqa: D103
    if value.startswith(("http://", "https://")):
        return value
    raise TypeError(f"{field} must start with http:// or https://")


def image(value: str, field: str):  # noqa: D103
    if value.endswith((".jpg", ".jpeg", ".png")):
        return value
    raise TypeError(f"{field} must end with .jpg or .png")


def positive(value: int, field: str):  # noqa: D103
    if value > 0:
        return value
    raise TypeError(f"{field} must be positive")


def non_negative(value: int, field: str):  # noqa: D103
    if value >= 0:
        return value
    raise TypeError(f"{field} must not be negative")


def episode_type(value: str, field: str):  # noqa: D103
    options = ["full", "trailer", "bonus"]
    if value in options:
        return value
    raise TypeError(f"{field} must be one of {' '.join(options)}")


def media_type(value: str, field: str):  # noqa: D103
    if value.endswith(tuple(mime_lookup.keys())):
        return value
    raise TypeError(f"{field} format must be one of "
                    f"{' '.join(mime_lookup.keys())}")


def to_timedelta(value: int, field: str):  # noqa: D103
    return timedelta(seconds=value)


def to_datetime(value: int, field: str):  # noqa: D103
    return datetime.fromtimestamp(value, timezone.utc)
