"""Migrate Grade table to support nullable CA/Exam/Total/Grade fields.

This migration preserves existing grade data while recreating the Grade table
with nullable score and letter columns required for IC (Incomplete) handling.

Usage:
    python migrate_grade_nullable.py
"""

from sqlalchemy import inspect

from app import app, db
from models import Grade


TARGET_COLUMNS = {
    "CA_score",
    "Exam_Score",
    "Total_Score",
    "Grade_Letter",
}


def _grade_table_needs_migration(engine):
    """Return True if any target Grade columns are still NOT NULL."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "grade" not in table_names:
        return False

    columns = inspector.get_columns("grade")
    for column in columns:
        if column["name"] in TARGET_COLUMNS and not column.get("nullable", True):
            return True
    return False


def migrate_grade_schema_nullable():
    """Recreate Grade table using current model metadata and restore all rows."""
    with app.app_context():
        engine = db.engine
        inspector = inspect(engine)

        if "grade" not in set(inspector.get_table_names()):
            print("Grade table not found. Creating schema from models...")
            db.create_all()
            print("Done.")
            return

        if not _grade_table_needs_migration(engine):
            print("Grade table already supports nullable score fields. No migration needed.")
            return

        print("Starting Grade schema migration...")

        existing_rows = Grade.query.order_by(Grade.grade_id.asc()).all()
        snapshot = [
            {
                "grade_id": row.grade_id,
                "enrollment_id": row.enrollment_id,
                "ca_score": row.ca_score,
                "exam_score": row.exam_score,
                "total_score": row.total_score,
                "grade_letter": row.grade_letter,
                "approval_status": row.approval_status,
            }
            for row in existing_rows
        ]

        print(f"Backed up {len(snapshot)} grade rows.")

        db.session.remove()
        Grade.__table__.drop(engine, checkfirst=True)
        Grade.__table__.create(engine, checkfirst=True)

        restored = 0
        for row in snapshot:
            db.session.add(
                Grade(
                    grade_id=row["grade_id"],
                    enrollment_id=row["enrollment_id"],
                    ca_score=row["ca_score"],
                    exam_score=row["exam_score"],
                    total_score=row["total_score"],
                    grade_letter=row["grade_letter"],
                    approval_status=row["approval_status"],
                )
            )
            restored += 1

        db.session.commit()
        print(f"Migration complete. Restored {restored} grade rows.")


if __name__ == "__main__":
    migrate_grade_schema_nullable()
