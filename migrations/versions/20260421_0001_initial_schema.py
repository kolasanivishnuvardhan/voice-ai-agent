"""Initial schema for voice AI appointment system."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260421_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create base tables and indexes."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    op.create_table(
        "patients",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("preferred_language", sa.String(length=5), server_default="en", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_patients"),
        sa.UniqueConstraint("phone", name="uq_patients_phone"),
    )

    op.create_table(
        "doctors",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("specialization", sa.String(length=100), nullable=False),
        sa.Column("hospital", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_doctors"),
    )
    op.create_index("ix_doctors_specialization", "doctors", ["specialization"], unique=False)

    op.create_table(
        "doctor_schedule",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("available_slots", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], name="fk_doctor_schedule_doctor_id_doctors", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_doctor_schedule"),
    )
    op.create_index("ix_doctor_schedule_date", "doctor_schedule", ["date"], unique=False)
    op.create_index("ix_doctor_schedule_doctor_id", "doctor_schedule", ["doctor_id"], unique=False)

    op.create_table(
        "appointments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("time", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], name="fk_appointments_doctor_id_doctors", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name="fk_appointments_patient_id_patients", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_appointments"),
    )
    op.create_index("ix_appointments_date", "appointments", ["date"], unique=False)
    op.create_index("ix_appointments_doctor_id", "appointments", ["doctor_id"], unique=False)
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"], unique=False)


def downgrade() -> None:
    """Drop schema in reverse order."""
    op.drop_index("ix_appointments_patient_id", table_name="appointments")
    op.drop_index("ix_appointments_doctor_id", table_name="appointments")
    op.drop_index("ix_appointments_date", table_name="appointments")
    op.drop_table("appointments")

    op.drop_index("ix_doctor_schedule_doctor_id", table_name="doctor_schedule")
    op.drop_index("ix_doctor_schedule_date", table_name="doctor_schedule")
    op.drop_table("doctor_schedule")

    op.drop_index("ix_doctors_specialization", table_name="doctors")
    op.drop_table("doctors")

    op.drop_table("patients")
