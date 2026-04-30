"""add execution tracking tables

Revision ID: 20260313_0001
Revises: None
Create Date: 2026-03-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260313_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级数据库架构"""
    op.create_table(
        "execution_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("execution_id", sa.String(), nullable=False),
        sa.Column("workflow_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("trigger_source", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("final_report_path", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_id"),
    )
    op.create_index("ix_execution_runs_execution_id", "execution_runs", ["execution_id"], unique=False)
    op.create_index("ix_execution_runs_workflow_id", "execution_runs", ["workflow_id"], unique=False)
    op.create_index("ix_execution_runs_status", "execution_runs", ["status"], unique=False)
    op.create_index(
        "idx_execution_runs_workflow_status",
        "execution_runs",
        ["workflow_id", "status"],
        unique=False
    )

    op.create_table(
        "execution_node_traces",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("execution_id", sa.String(), nullable=False),
        sa.Column("node_id", sa.String(), nullable=False),
        sa.Column("node_type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=True),
        sa.Column("output_payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["execution_runs.execution_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_execution_node_traces_execution_id", "execution_node_traces", ["execution_id"], unique=False)
    op.create_index("ix_execution_node_traces_node_id", "execution_node_traces", ["node_id"], unique=False)
    op.create_index("ix_execution_node_traces_status", "execution_node_traces", ["status"], unique=False)
    op.create_index(
        "idx_execution_node_trace_exec_node",
        "execution_node_traces",
        ["execution_id", "node_id"],
        unique=False
    )


def downgrade() -> None:
    """回滚数据库架构"""
    op.drop_index("idx_execution_node_trace_exec_node", table_name="execution_node_traces")
    op.drop_index("ix_execution_node_traces_status", table_name="execution_node_traces")
    op.drop_index("ix_execution_node_traces_node_id", table_name="execution_node_traces")
    op.drop_index("ix_execution_node_traces_execution_id", table_name="execution_node_traces")
    op.drop_table("execution_node_traces")

    op.drop_index("idx_execution_runs_workflow_status", table_name="execution_runs")
    op.drop_index("ix_execution_runs_status", table_name="execution_runs")
    op.drop_index("ix_execution_runs_workflow_id", table_name="execution_runs")
    op.drop_index("ix_execution_runs_execution_id", table_name="execution_runs")
    op.drop_table("execution_runs")