import os
import sys
import time

# Setup paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from database import SessionLocal
from models import Problem, TestCase
from tools.auto_testcase_gen import auto_generate_testcases

def run_bulk_generation():
    db = SessionLocal()
    try:
        # Category: Tin học cơ sở 2
        CATEGORY_SLUG = "tin-hoc-co-so-2"
        
        problems = db.query(Problem).filter(Problem.category == CATEGORY_SLUG).all()
        print(f"Found {len(problems)} problems in category '{CATEGORY_SLUG}'")
        
        success_count = 0
        fail_count = 0
        
        for p in problems:
            # Count existing testcases
            tc_count = db.query(TestCase).filter(TestCase.problem_id == p.id).count()
            
            if tc_count < 10:
                needed = 10 - tc_count
                print(f"\n--- Problem {p.code}: {tc_count} testcases. Generating {needed} more ---")
                
                # Sleep to avoid 429 quota issues
                time.sleep(15)
                
                # Try up to 2 times for each problem
                for attempt in range(2):
                    try:
                        count, err = auto_generate_testcases(p.code, needed)
                        if count > 0:
                            print(f"  SUCCESS: Generated {count} testcases for {p.code}")
                            success_count += 1
                            break
                        else:
                            if "429" in str(err):
                                print(f"  WAITING (429 Quota): Sleeping 60s...")
                                time.sleep(60)
                                continue
                            print(f"  FAILED: {err}")
                            if attempt == 1: fail_count += 1
                    except Exception as e:
                        print(f"  ERROR processing {p.code}: {str(e)}")
                        if attempt == 1: fail_count += 1
                        time.sleep(5)
            else:
                # No sleep needed for skipped problems
                pass
        
        print(f"\nBulk Generation Finished.")
        print(f"Successfully processed: {success_count} problems")
        print(f"Failed: {fail_count} problems")
                
    finally:
        db.close()

if __name__ == "__main__":
    run_bulk_generation()
