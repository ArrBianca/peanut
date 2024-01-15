"""create category table

Revision ID: 7c4972557441
Revises:
Create Date: 2024-01-15 13:47:58.899403

"""
from typing import List, Optional, Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import ForeignKey, orm
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

# revision identifiers, used by Alembic.
revision: str = '7c4972557441'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

Base = declarative_base()


# Basic Podcast table model
class Podcast(Base):
    __tablename__ = 'podcast'
    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[Optional[str]]
    categories: Mapped[List["Category"]] = relationship()


class Category(Base):
    __tablename__ = 'category'
    id: Mapped[int] = mapped_column(primary_key=True)
    podcast_id: Mapped[int] = mapped_column(ForeignKey("podcast.id"))
    cat: Mapped[str]
    sub: Mapped[Optional[str]]


def upgrade() -> None:
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    Category.__table__.create(bind=bind)

    for podcast in session.query(Podcast):
        cat = Category(
            podcast_id=podcast.id,
            cat=podcast.category,
        )
        session.add(cat)

    op.drop_column('podcast', 'category')

    session.commit()


def downgrade() -> None:
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    op.add_column('podcast', sa.Column('category', sa.String, nullable=True))
    for podcast in session.query(Podcast):
        for category in podcast.categories:
            podcast.category = category.cat
    op.drop_table('category')

    session.commit()
    pass
