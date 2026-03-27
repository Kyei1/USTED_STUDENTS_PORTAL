"""Normalize legacy Grade exam scores from 60-scale component to raw 100-scale.

Older seed data stored Grade.exam_score as an exam component out of 60 instead of
raw score out of 100. This script detects those rows and converts them in-place.

Detection rule:
- Compare stored total against:
  1) CA + scaled(raw_exam) where scaled(raw_exam) = raw_exam/100 * 60
  2) CA + exam_score (legacy component)
- If (2) is much closer, treat row as legacy and normalize.

Usage:
    python normalize_legacy_exam_scores.py
"""

from app import app, db
from models import Grade
from services import score_to_letter, scaled_exam_score


def normalize_legacy_exam_scores():
    """Convert legacy exam component values to raw exam scores and refresh totals."""
    with app.app_context():
        rows = Grade.query.all()
        normalized = 0

        for row in rows:
            if row.ca_score is None or row.exam_score is None or row.total_score is None:
                continue

            ca = float(row.ca_score)
            exam_value = float(row.exam_score)
            stored_total = float(row.total_score)

            total_from_raw = round(ca + scaled_exam_score(exam_value), 2)
            total_from_component = round(ca + exam_value, 2)

            raw_gap = abs(stored_total - total_from_raw)
            component_gap = abs(stored_total - total_from_component)

            # Legacy signature: total matches CA + exam_component much better.
            if component_gap <= 1.0 and raw_gap > 1.5:
                normalized_raw_exam = min(100.0, round((exam_value / 60.0) * 100.0, 2))
                normalized_total = round(ca + scaled_exam_score(normalized_raw_exam), 2)

                row.exam_score = normalized_raw_exam
                row.total_score = normalized_total
                row.grade_letter = score_to_letter(normalized_total)
                normalized += 1

        if normalized:
            db.session.commit()
            print(f"Normalized {normalized} legacy grade row(s).")
        else:
            print("No legacy exam rows detected. Nothing changed.")


if __name__ == '__main__':
    normalize_legacy_exam_scores()
