"""Reset database and apply schema with updated ERD constraints.

This script:
1. Drops all existing tables (using db.drop_all())
2. Recreates tables with updated schema (using db.create_all())
3. Populates with comprehensive seed data (from seed_db.py)

Usage: python reset_db.py
"""

import os
from pathlib import Path

from app import app, db


def reset_database():
	"""Drop all tables, recreate schema from updated models, and seed with test data."""
	with app.app_context():
		print("\n" + "="*70)
		print("USTED STUDENTS PORTAL - DATABASE RESET")
		print("="*70)
		
		db_path = Path('instance/usted_portal.db')
		
		# Remove existing database file
		if db_path.exists():
			db_path.unlink()
			print(f"\n[1/3] ✓ Removed existing database: {db_path}")
		else:
			print(f"\n[1/3] ✓ No existing database found (fresh start)")
		
		# Drop all tables (ensures clean slate)
		db.drop_all()
		print("[2/3] ✓ Dropped all tables (if any existed)")
		
		# Recreate all tables with updated schema
		db.create_all()
		print("[3/3] ✓ Recreated database schema with updated constraints:")
		print("     - Lecturer.role defaults to 'Lecturer'")
		print("     - Resource.course_code is nullable (Department OR Course)")
		print("     - FinancialStatus unique constraint on (student_id, academic_year)")
		print("     - Grade CA/Exam/Total/Letter fields allow NULL for IC handling")
		print("     - All enum values validated per ERD rules")
		
		# Import and run comprehensive seed script
		print("\nSeeding database with comprehensive institutional data...")
		from seed_db import seed_initial_data
		seed_initial_data(reset_schema=False)
		
		print("\n" + "="*70)
		print(" DATABASE RESET AND SEED COMPLETE")
		print("="*70)
		print("\n Next Steps:")
		print("  1. Run 'python app.py' to start the portal")
		print("  2. Login credentials:")
		print("     - Student ID: USD260012")
		print("     - Password: password123")
		print("="*70 + "\n")


if __name__ == '__main__':
	reset_database()
