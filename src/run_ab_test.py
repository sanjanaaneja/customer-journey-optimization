# run the ab test

import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from ab_test import run_ab_test

results = run_ab_test()

print("=" * 50)
print("RESULTS SUMMARY")
print("=" * 50)
for key, value in results.items():
    print(f"  {key}: {value}")
