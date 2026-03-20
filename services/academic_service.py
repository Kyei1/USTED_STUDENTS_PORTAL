"""Academic period and enrollment utilities for the USTED Students Portal."""


def semester_rank(semester):
    """Rank semester for sorting (First=1, Second=2)."""
    return 2 if semester == 'Second' else 1


def academic_period_rank(enrollment):
    """
    Create a sortable rank tuple for academic periods.
    
    Returns tuple of (start_year, semester_rank) for proper chronological sorting.
    """
    try:
        start_year = int(str(enrollment.academic_year).split('/')[0])
    except (ValueError, IndexError):
        start_year = 0
    return (start_year, semester_rank(enrollment.semester))
