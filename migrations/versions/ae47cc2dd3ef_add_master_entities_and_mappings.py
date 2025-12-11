"""add_master_entities_and_mappings

Revision ID: ae47cc2dd3ef
Revises: dd46bb1cc2bd
Create Date: 2025-12-12 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ae47cc2dd3ef'
down_revision: Union[str, None] = 'dd46bb1cc2bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create master_entities table
    op.create_table(
        'master_entities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('canonical_symbol', sa.String(length=20), nullable=False),
        sa.Column('canonical_name', sa.String(length=200), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('primary_source', sa.String(length=50), nullable=False),
        sa.Column('primary_coin_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('canonical_symbol')
    )
    op.create_index('ix_master_entities_symbol_name', 'master_entities', ['canonical_symbol', 'canonical_name'])
    op.create_index(op.f('ix_master_entities_canonical_symbol'), 'master_entities', ['canonical_symbol'], unique=True)
    
    # Create entity_mappings table
    op.create_table(
        'entity_mappings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('master_entity_id', sa.Integer(), nullable=False),
        sa.Column('coin_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=5, scale=3), nullable=True),
        sa.Column('is_primary', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('coin_id', name='uq_coin_id')
    )
    op.create_index('ix_entity_mappings_master_entity', 'entity_mappings', ['master_entity_id'])
    op.create_index('ix_entity_mappings_source', 'entity_mappings', ['source', 'master_entity_id'])
    op.create_index(op.f('ix_entity_mappings_coin_id'), 'entity_mappings', ['coin_id'])


def downgrade() -> None:
    # Drop entity_mappings table
    op.drop_index(op.f('ix_entity_mappings_coin_id'), table_name='entity_mappings')
    op.drop_index('ix_entity_mappings_source', table_name='entity_mappings')
    op.drop_index('ix_entity_mappings_master_entity', table_name='entity_mappings')
    op.drop_table('entity_mappings')
    
    # Drop master_entities table
    op.drop_index(op.f('ix_master_entities_canonical_symbol'), table_name='master_entities')
    op.drop_index('ix_master_entities_symbol_name', table_name='master_entities')
    op.drop_table('master_entities')
