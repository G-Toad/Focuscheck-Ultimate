"""
Simple terminal-based codex analysis runner
Runs multiple codex instances and saves results
"""

import subprocess
import os
import time
from pathlib import Path
from datetime import datetime

# Configuration
WORKING_DIR = Path(__file__).parent
RESULTS_DIR = WORKING_DIR / "codex_analysis_results"
RESULTS_DIR.mkdir(exist_ok=True)

# Analysis prompts
PROMPTS = [
    "Analyze main.py and focuscheck/__init__.py for import errors, circular dependencies, and module loading issues",
    "Analyze focuscheck/app.py for threading issues, race conditions, and resource cleanup problems",
    "Analyze focuscheck/settings/ directory for configuration bugs, validation errors, and data persistence issues",
    "Analyze focuscheck/ui/ directory for GUI bugs, event handling issues, and memory leaks",
    "Analyze focuscheck/database/ directory for SQL injection risks, transaction issues, and data integrity problems",
    "Analyze focuscheck/utils/ directory for utility function bugs, error handling issues, and edge cases",
    "Analyze focuscheck/platform_specific/ for Windows API usage bugs, registry issues, and compatibility problems",
    "Check all files for exception handling issues, uncaught errors, and improper error recovery",
    "Check for resource leaks, file handle leaks, database connection leaks, and memory issues",
    "Analyze for concurrency bugs, deadlocks, race conditions in multi-threaded code",
]

def run_codex_instance(instance_num, prompt):
    """Run a single codex instance"""
    print(f"\n[Instance {instance_num}] Starting...")
    print(f"[Instance {instance_num}] Prompt: {prompt[:80]}...")

    output_file = RESULTS_DIR / f"instance_{instance_num}.txt"

    cmd = f'codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -C "{WORKING_DIR}" "{prompt}"'

    try:
        start_time = time.time()

        # Run in background and save to file
        with open(output_file, 'w') as f:
            process = subprocess.Popen(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=str(WORKING_DIR),
                shell=True
            )

        print(f"[Instance {instance_num}] Running in background (PID: {process.pid})")
        print(f"[Instance {instance_num}] Output: {output_file}")

        return {
            'num': instance_num,
            'process': process,
            'start_time': start_time,
            'output_file': output_file,
            'prompt': prompt
        }

    except Exception as e:
        print(f"[Instance {instance_num}] ERROR: {e}")
        return None

def main():
    print("="*80)
    print("FOCUSCHECK CODEX ANALYSIS - BACKGROUND RUNNER")
    print("="*80)
    print(f"Working Directory: {WORKING_DIR}")
    print(f"Results Directory: {RESULTS_DIR}")
    print(f"Number of Instances: {len(PROMPTS)}")
    print("="*80)

    # Start all instances
    instances = []
    for i, prompt in enumerate(PROMPTS, 1):
        instance = run_codex_instance(i, prompt)
        if instance:
            instances.append(instance)
        time.sleep(2)  # Small delay between starts

    print(f"\n{'='*80}")
    print(f"ALL {len(instances)} INSTANCES STARTED IN BACKGROUND")
    print("="*80)
    print("\nMonitoring progress...\n")

    # Monitor completion
    while instances:
        time.sleep(10)

        completed = []
        for instance in instances:
            if instance['process'].poll() is not None:
                runtime = time.time() - instance['start_time']
                print(f"[Instance {instance['num']}] COMPLETED in {int(runtime)}s")
                completed.append(instance)

        # Remove completed
        for inst in completed:
            instances.remove(inst)

        if instances:
            print(f"Still running: {len(instances)} instances...")

    print("\n" + "="*80)
    print("ALL INSTANCES COMPLETED!")
    print("="*80)

    # Create completion marker
    marker = WORKING_DIR / "CODEX_ANALYSIS_COMPLETE.txt"
    with open(marker, 'w') as f:
        f.write(f"Analysis completed at {datetime.now()}\n")
        f.write(f"Results saved in: {RESULTS_DIR}\n")

    print(f"\nResults saved in: {RESULTS_DIR}")
    print(f"Completion marker: {marker}")
    print("\nDONE! Check the results directory for all outputs.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    except Exception as e:
        print(f"\n\nERROR: {e}")
