"""Add transcript

Revision ID: 56964ef7b70c
Revises: 3e421584fdaa
Create Date: 2024-02-10 14:35:20.801001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '56964ef7b70c'
down_revision: Union[str, None] = '3e421584fdaa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("episode", sa.Column("transcript", sa.String))
    op.add_column("episode", sa.Column("transcript_type", sa.String))


def downgrade() -> None:
    op.drop_column("episode", "transcript_type")
    op.drop_column("episode", "transcript")
