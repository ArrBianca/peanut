"""alter nullability

Revision ID: 3e421584fdaa
Revises: 95337e33ecd9
Create Date: 2024-01-19 12:40:37.470559

"""
from typing import Sequence, Union
from uuid import uuid4
import sqlalchemy as sa
from alembic import op
from alembic.operations import BatchOperations

# revision identifiers, used by Alembic.
revision: str = '3e421584fdaa'
down_revision: Union[str, None] = '95337e33ecd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('podcast', recreate='always') as alter_podcast:
        alter_podcast: BatchOperations = alter_podcast  # PyCharm doesn't detect, is all.

        alter_podcast.alter_column('explicit', server_default=False)
        alter_podcast.alter_column('image', nullable=True)
        alter_podcast.alter_column('author', nullable=True)
        alter_podcast.alter_column('language', nullable=True)
        alter_podcast.alter_column('auth_token', nullable=True)
        alter_podcast.alter_column('last_build_date', nullable=False)

    with op.batch_alter_table('episode', recreate='always') as alter_episode:
        alter_episode: BatchOperations = alter_episode  # As before.
        alter_episode.alter_column('episode_type', nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('podcast', recreate='always') as alter_podcast:
        alter_podcast: BatchOperations = alter_podcast  # PyCharm doesn't detect, is all.

        alter_podcast.alter_column('explicit', server_default=None)
        alter_podcast.alter_column('image', nullable=False)
        alter_podcast.alter_column('author', nullable=False)
        alter_podcast.alter_column('language', nullable=False)
        alter_podcast.alter_column('auth_token', nullable=False)
        alter_podcast.alter_column('last_build_date', nullable=True)

        with op.batch_alter_table('episode', recreate='always') as alter_episode:
            alter_episode: BatchOperations = alter_episode  # As before.
            alter_episode.alter_column('episode_type', nullable=False)
