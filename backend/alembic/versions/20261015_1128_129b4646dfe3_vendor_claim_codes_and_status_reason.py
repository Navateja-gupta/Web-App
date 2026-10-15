"""vendor claim codes and status reason

Revision ID: 129b4646dfe3
Revises: 14a55976a576
Create Date: 2026-10-15 11:28:15.969442

* Renames vendors.rejection_reason -> status_reason (also used for suspensions).
  Edited by hand: autogenerate proposed drop + add, which would lose existing data.
* Adds one-time claim-code columns for linking admin-created profiles to vendor accounts.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '129b4646dfe3'
down_revision: Union[str, None] = '14a55976a576'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('vendors', 'rejection_reason', new_column_name='status_reason')
    op.add_column('vendors', sa.Column('claim_code_hash', sa.String(length=64), nullable=True))
    op.add_column('vendors', sa.Column('claim_code_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint(op.f('uq_vendors_claim_code_hash'), 'vendors', ['claim_code_hash'])


def downgrade() -> None:
    op.drop_constraint(op.f('uq_vendors_claim_code_hash'), 'vendors', type_='unique')
    op.drop_column('vendors', 'claim_code_expires_at')
    op.drop_column('vendors', 'claim_code_hash')
    op.alter_column('vendors', 'status_reason', new_column_name='rejection_reason')
