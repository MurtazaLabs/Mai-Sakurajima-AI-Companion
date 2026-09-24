"""Initial migration - create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-09-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create profiles table
    op.create_table(
        'profiles',
        sa.Column('profile_id', sa.String(36), primary_key=True),
        sa.Column('display_name', sa.String(100), nullable=True),
        sa.Column('preferences', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('session_id', sa.String(36), primary_key=True),
        sa.Column('profile_id', sa.String(36), sa.ForeignKey('profiles.profile_id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_activity', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
    )
    op.create_index('ix_sessions_profile_id', 'sessions', ['profile_id'])
    op.create_index('ix_sessions_expires_at', 'sessions', ['expires_at'])
    
    # Create memory_nodes table
    op.create_table(
        'memory_nodes',
        sa.Column('node_id', sa.String(64), primary_key=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('memory_type', sa.String(50), nullable=False),
        sa.Column('importance', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('emotion', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('tags', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('speaker', sa.String(50), nullable=True),
        sa.Column('user_id', sa.String(36), nullable=True, index=True),
        sa.Column('vector_id', sa.String(64), nullable=True),
        sa.Column('source', sa.String(255), nullable=True),
sa.Column('timestamp', sa.Float(), nullable=False, server_default=sa.text('(strftime(\'%s\', \'now\'))')), 
        sa.Column('access_count', sa.Float(), nullable=False, server_default='0'), 
        sa.Column('schema_version', sa.Integer(), nullable=False, server_default='1'),
    )
    op.create_index('ix_memory_nodes_memory_type', 'memory_nodes', ['memory_type'])
    op.create_index('ix_memory_nodes_user_id', 'memory_nodes', ['user_id'])
    op.create_index('ix_memory_nodes_timestamp', 'memory_nodes', ['timestamp'])
    
    # Create relationship_evidence table
    op.create_table(
        'relationship_evidence',
        sa.Column('evidence_id', sa.String(36), primary_key=True),
        sa.Column('timestamp', sa.Float(), nullable=False, index=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('dimension_impacts', sa.JSON(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_relationship_evidence_timestamp', 'relationship_evidence', ['timestamp'])
    
    # Create shared_state table (singleton)
    op.create_table(
        'shared_state',
        sa.Column('id', sa.String(36), primary_key=True, server_default='singleton'),
        sa.Column('emotion', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('relationship_scores', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('goals', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('attention', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('runtime', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create evidence table (legacy SQLite compatibility)
    op.create_table(
        'evidence',
        sa.Column('evidence_id', sa.String(36), primary_key=True),
        sa.Column('timestamp', sa.Float(), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('dimension_impacts', sa.JSON(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('evidence')
    op.drop_table('shared_state')
    op.drop_table('relationship_evidence')
    op.drop_table('memory_nodes')
    op.drop_table('sessions')
    op.drop_table('profiles')