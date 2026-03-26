"""Services module for business logic and data access."""

from services.student_service import (
    get_current_student,
    build_next_period,
    build_semester_course_offering,
    build_past_period_catalog,
)
from services.gpa_service import (
    score_to_point,
    score_to_letter,
    classify_cgpa,
    point_to_min_total_score,
    scaled_exam_score,
    course_difficulty_weight,
    difficulty_label,
    allocate_uneven_target_points,
)
from services.academic_service import (
    semester_rank,
    academic_period_rank,
    compute_results_analytics,
    build_semester_number_lookup,
    group_records_by_period,
)
from services.pdf_service import (
    get_default_logo_path,
    draw_logo_and_titles,
    draw_two_column_metadata,
)
from services.lecturer_service import (
    build_lecturer_course_worklist,
    build_lecturer_draft_workspace,
    build_lecturer_resource_hub,
    submit_lecturer_drafts_to_hod,
)

__all__ = [
    'get_current_student',
    'build_next_period',
    'build_semester_course_offering',
    'build_past_period_catalog',
    'score_to_point',
    'score_to_letter',
    'classify_cgpa',
    'point_to_min_total_score',
    'scaled_exam_score',
    'course_difficulty_weight',
    'difficulty_label',
    'allocate_uneven_target_points',
    'semester_rank',
    'academic_period_rank',
    'compute_results_analytics',
    'build_semester_number_lookup',
    'group_records_by_period',
    'get_default_logo_path',
    'draw_logo_and_titles',
    'draw_two_column_metadata',
    'build_lecturer_course_worklist',
    'build_lecturer_draft_workspace',
    'build_lecturer_resource_hub',
    'submit_lecturer_drafts_to_hod',
]
