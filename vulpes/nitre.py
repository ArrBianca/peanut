from datetime import timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime, TypeDecorator
from sqlalchemy.orm import DeclarativeBase


# Recipe from https://docs.sqlalchemy.org/en/20/core/custom_types.html#store-timezone-aware-timestamps-as-timezone-naive-utc
class TZDateTime(TypeDecorator):
    """A DateTime type that enforces timezone-aware-ness."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Only store aware datetimes to the db."""
        if value is not None:
            if not value.tzinfo or value.tzinfo.utcoffset(value) is None:
                raise TypeError("tzinfo is required")
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        """On retrieval, we set UTC time and strip microseconds."""
        if value is not None:
            value = value.replace(tzinfo=timezone.utc,
                                  microsecond=0)
        return value


class Base(DeclarativeBase):
    """The DeclarativeBase you have to use in sqlalchemy."""

    pass


db = SQLAlchemy(model_class=Base)
