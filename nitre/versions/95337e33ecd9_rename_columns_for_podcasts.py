"""rename columns for podcasts

Revision ID: 95337e33ecd9
Revises: 7c4972557441
Create Date: 2024-01-17 17:32:20.979125

"""
from datetime import datetime
from typing import Literal, Optional, Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Column, orm
from sqlalchemy.orm import Mapped, Session, mapped_column

# revision identifiers, used by Alembic.
revision: str = '95337e33ecd9'
down_revision: Union[str, None] = '7c4972557441'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

Base = orm.declarative_base()


class Podcast(Base):
    __tablename__ = 'podcast'
    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str]
    website: Mapped[str]
    author_name: Mapped[str]
    withhold_from_itunes: Mapped[bool] = mapped_column(default=False)

    title: Mapped[str]
    link: Mapped[str]
    author: Mapped[str]
    itunes_block: Mapped[bool] = mapped_column(default=False)

    new_feed_url: Mapped[Optional[str]] = mapped_column(nullable=True)
    complete: Mapped[bool] = mapped_column(default=False)


class Episode(Base):
    __tablename__ = 'episode'
    id: Mapped[int] = mapped_column(primary_key=True)
    summary: Mapped[Optional[str]]
    long_summary: Mapped[Optional[str]]
    episode_art: Mapped[Optional[str]]
    last_modified: Mapped[Optional[datetime]]

    description: Mapped[Optional[str]]
    image: Mapped[Optional[str]]
    last_build_date: Mapped[Optional[datetime]]

    # explicit: Mapped[bool] = mapped_column(default=False)
    episode_type: Mapped[Literal["full", "trailer", "bonus"]] = mapped_column(default='full')
    season: Mapped[Optional[int]]
    episode: Mapped[Optional[int]]


def upgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)
    Podcast.metadata.create_all(bind=bind)
    op.alter_column('podcast', 'name', new_column_name='title')
    op.alter_column('podcast', 'website', new_column_name='link')
    op.alter_column('podcast', 'author_name', new_column_name='author')
    op.alter_column('podcast', 'withhold_from_itunes', new_column_name='itunes_block')
    op.alter_column('podcast', 'last_modified', new_column_name='last_build_date')

    with op.batch_alter_table('podcast', recreate="always") as alter_podcats:
        alter_podcats.add_column(Column('new_feed_url', sa.String(), nullable=True), insert_after='itunes_block')
        alter_podcats.add_column(Column('complete', sa.Boolean(), default=False), insert_after='new_feed_url')

    with op.batch_alter_table('episode', recreate='always') as batch_op:
        batch_op.drop_constraint('title_summary_check')

        batch_op.drop_column('summary')

        batch_op.alter_column('title', nullable=False)
        batch_op.alter_column('long_summary', new_column_name='description')
        batch_op.alter_column('episode_art', new_column_name='image')

        # batch_op.add_column(Column('explicit', sa.Boolean(), default=False))
        batch_op.add_column(Column('episode_type', sa.String(length=7), nullable=True))
        batch_op.add_column(Column('season', sa.Integer(), nullable=True))
        batch_op.add_column(Column('episode', sa.Integer(), nullable=True))
    # Episode.metadata.add_column(Episode.season)
    # Episode.metadata.create_all(bind=bind)
    # session.commit()
    # op.drop_column('episode', 'summary')
    session.commit()
    pass


def downgrade() -> None:
    pass
