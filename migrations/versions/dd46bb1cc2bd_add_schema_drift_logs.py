"""add_schema_drift_logs

Revision ID: dd46bb1cc2bd
Revises: 87a16f9bdf61
Create Date: 2025-12-09 10:59:30.584763

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'dd46bb1cc2bd'
down_revision: Union[str, None] = '87a16f9bdf61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'schema_drift_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=True),
        sa.Column('schema_name', sa.String(length=100), nullable=False),
        sa.Column('confidence_score', sa.Numeric(precision=5, scale=3), nullable=True),
        sa.Column('missing_fields', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('extra_fields', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('fuzzy_matches', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('warnings', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_schema_drift_source_detected', 'schema_drift_logs', ['source', 'detected_at'])
    op.create_index(op.f('ix_schema_drift_logs_detected_at'), 'schema_drift_logs', ['detected_at'])
    op.create_index(op.f('ix_schema_drift_logs_run_id'), 'schema_drift_logs', ['run_id'])
    op.create_index(op.f('ix_schema_drift_logs_source'), 'schema_drift_logs', ['source'])


def downgrade() -> None:
    op.drop_index(op.f('ix_schema_drift_logs_source'), table_name='schema_drift_logs')
    op.drop_index(op.f('ix_schema_drift_logs_run_id'), table_name='schema_drift_logs')
    op.drop_index(op.f('ix_schema_drift_logs_detected_at'), table_name='schema_drift_logs')
    op.drop_index('ix_schema_drift_source_detected', table_name='schema_drift_logs')
    op.drop_table('schema_drift_logs')
