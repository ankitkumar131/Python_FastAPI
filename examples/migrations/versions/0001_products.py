from alembic import op
import sqlalchemy as sa

revision = "0001_products"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.UniqueConstraint("name", name="uq_products_name"),
        sa.CheckConstraint("price_minor >= 0", name="ck_products_price"),
    )

def downgrade():
    op.drop_table("products")
