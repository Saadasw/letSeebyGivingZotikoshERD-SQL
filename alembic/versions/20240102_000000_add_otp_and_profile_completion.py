"""Add OTP table and profile completion fields

Revision ID: 002_otp_profile
Revises: 001_initial
Create Date: 2024-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_otp_profile'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create OTP purpose enum
    op.execute("""
        CREATE TYPE otp_purpose AS ENUM (
            'email_verification',
            'password_reset',
            'phone_verification'
        );
    """)

    # Create OTP table
    op.create_table(
        'otp',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('otp_code', sa.String(6), nullable=False),
        sa.Column('purpose', postgresql.ENUM('email_verification', 'password_reset', 'phone_verification', name='otp_purpose', create_type=False), nullable=False, default='email_verification'),
        sa.Column('is_verified', sa.Boolean, default=False, nullable=False),
        sa.Column('attempts', sa.Integer, default=0, nullable=False),
        sa.Column('max_attempts', sa.Integer, default=3, nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_otp_email', 'otp', ['email'])
    op.create_index('ix_otp_email_purpose', 'otp', ['email', 'purpose'])

    # Add profile_completed and profile_completed_at to user table
    op.add_column('user', sa.Column('profile_completed', sa.Boolean, default=False, nullable=False, server_default='false'))
    op.add_column('user', sa.Column('profile_completed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove columns from user table
    op.drop_column('user', 'profile_completed_at')
    op.drop_column('user', 'profile_completed')

    # Drop OTP table
    op.drop_index('ix_otp_email_purpose', table_name='otp')
    op.drop_index('ix_otp_email', table_name='otp')
    op.drop_table('otp')

    # Drop OTP purpose enum
    op.execute("DROP TYPE IF EXISTS otp_purpose;")
