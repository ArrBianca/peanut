from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Sequence

from .jxml import media_mime, transcript_mime


def _en_join_list(terms: Sequence[str], joiner: str = "or") -> str:
    match len(terms):
        case 1:
            return terms[0]
        case 2:
            return f"{joiner} ".join(terms)
        case _:
            return ", ".join(terms[:-1]) + f", {joiner} " + terms[-1]


class Pull:
    """Dict-to-dict value extractor and rule checker."""

    def __init__(
            self,
            from_,
            *rules: Callable,
            required: bool = False,
            to: str | None = None,
            default: Any | None = None,
            alongside: list[str] | None = None,
    ):
        """Set up a value to be pulled from a dict and processed.

        :param from_: The dict key to take the value from.
        :param rules: zero to several callables like the ones below
            that take the value as well as its key name for error
            formatting, and transform or validate the value. Raise a
            TypeError if the value does not pass validation, return
            the value unaltered if no changes are made.
        :param required: whether processing should abort on a missing,
            defaultless value.
        :param to: the name of the key in the result dict. If left as
            None, `from_` is used.
        :param default: A default value to use if the key is not present
            in the source. Necessarily overrules `required` if set.
        :param alongside: A list of keys that are required to be
            in the source alongside this one, allowing for groups of
            values that need to be together.This should be set on all
            sides of the relationship.
        """
        self.from_ = from_
        self.rules = rules
        self.required = required
        self.to = to or from_
        self.default = default
        # This will get unwieldy with larger sets of values.
        self.alongside = alongside or []

    def run(self, source: dict) -> Any:
        """Pull the value.

        Grab a specified value from a dictionary, apply a chain of
        callables for conversion and validation, and return the result.
        Or error out.
        """
        value = source.get(self.from_)
        if value is None:
            if self.default is not None:
                return self.default
            if self.required:
                raise ValueError(f"{self.from_} missing.")
            return None

        for other in self.alongside:
            if other not in source:
                raise ValueError(
                    f"{self.from_} can only be specified together with "
                    f"{_en_join_list(self.alongside, 'and')}.")

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


def episode_types(value: str, field: str):  # noqa: D103
    options = ["full", "trailer", "bonus"]
    if value in options:
        return value
    raise TypeError(f"{field} must be one of {_en_join_list(options)}")


# noinspection PyUnusedLocal
def as_timedelta(value: int, field: str):  # noqa: D103
    return timedelta(seconds=value)


# noinspection PyUnusedLocal
def as_datetime(value: int, field: str):  # noqa: D103
    return datetime.fromtimestamp(value, timezone.utc)


def _extension_rule(extensions: tuple[str]) -> Callable[[str, str], str]:
    def rule(value: str, field: str):
        if value.endswith(extensions):
            return value
        raise TypeError(f"{field} must be one of {_en_join_list(extensions)}")
    return rule


media_exts = _extension_rule(tuple(media_mime.keys()))
transcript_exts = _extension_rule(tuple(transcript_mime.keys()))
