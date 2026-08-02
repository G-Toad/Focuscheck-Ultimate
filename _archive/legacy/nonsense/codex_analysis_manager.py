"""
Codex Analysis Manager - Background Bug Testing System
Runs multiple codex instances and consolidates results with GUI monitoring
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import time
import json
import os
import re
from datetime import datetime
from pathlib import Path

class CodexAnalysisManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Codex Analysis Manager - FocusCheck Bug Testing")
        self.root.geometry("1200x800")

        # Configuration
        self.working_dir = Path(__file__).parent
        self.results_dir = self.working_dir / "codex_analysis_results"
        self.results_dir.mkdir(exist_ok=True)

        # State tracking
        self.instances = []
        self.processes = {}
        self.results = {}
        self.token_usage = {}
        self.is_running = False

        # Analysis prompts for different aspects
        self.analysis_prompts = [
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
            "Check for input validation issues, boundary conditions, and edge case handling",
            "Analyze for logic errors, incorrect algorithms, and calculation mistakes",
            "Check for code quality issues, code smells, and potential refactoring opportunities",
            "Analyze UI dialogs in focuscheck/ui/dialogs/ for usability issues and bugs",
            "Check audio system in focuscheck/utils/audio.py for audio playback bugs and device issues",
            "Analyze system tray integration for notification bugs and menu issues",
            "Check pause guard and auto-pause logic for timing bugs and detection issues",
            "Analyze task database operations for CRUD bugs and query optimization issues",
            "Check CSV logging system for data corruption risks and file handling issues",
            "Perform comprehensive security audit for vulnerabilities and security risks"
        ]

        self.setup_ui()

    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Title
        title = ttk.Label(main_frame, text="FocusCheck Codex Analysis Manager",
                         font=('Arial', 16, 'bold'))
        title.grid(row=0, column=0, pady=10, sticky=tk.W)

        # Control panel
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(control_frame, text="Number of Instances:").grid(row=0, column=0, padx=5)
        self.num_instances_var = tk.IntVar(value=10)
        instances_spin = ttk.Spinbox(control_frame, from_=1, to=100,
                                     textvariable=self.num_instances_var, width=10)
        instances_spin.grid(row=0, column=1, padx=5)

        self.start_btn = ttk.Button(control_frame, text="Start Analysis",
                                    command=self.start_analysis)
        self.start_btn.grid(row=0, column=2, padx=10)

        self.stop_btn = ttk.Button(control_frame, text="Stop All",
                                   command=self.stop_analysis, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=3, padx=5)

        ttk.Button(control_frame, text="View Consolidated Report",
                  command=self.view_report).grid(row=0, column=4, padx=5)

        # Status panel
        status_frame = ttk.LabelFrame(main_frame, text="Overall Status", padding="10")
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(1, weight=1)

        # Progress bar
        progress_container = ttk.Frame(status_frame)
        progress_container.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        progress_container.columnconfigure(1, weight=1)

        ttk.Label(progress_container, text="Overall Progress:").grid(row=0, column=0, padx=5)
        self.overall_progress = ttk.Progressbar(progress_container, mode='determinate')
        self.overall_progress.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)

        self.progress_label = ttk.Label(progress_container, text="0/0 completed")
        self.progress_label.grid(row=0, column=2, padx=5)

        # Instance list
        self.instance_tree = ttk.Treeview(status_frame,
                                         columns=("status", "tokens", "time", "result"),
                                         show="tree headings", height=15)
        self.instance_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        self.instance_tree.heading("#0", text="Instance")
        self.instance_tree.heading("status", text="Status")
        self.instance_tree.heading("tokens", text="Tokens Used")
        self.instance_tree.heading("time", text="Runtime")
        self.instance_tree.heading("result", text="Result")

        self.instance_tree.column("#0", width=400)
        self.instance_tree.column("status", width=100)
        self.instance_tree.column("tokens", width=100)
        self.instance_tree.column("time", width=100)
        self.instance_tree.column("result", width=200)

        # Scrollbar
        scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL,
                                 command=self.instance_tree.yview)
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.instance_tree.configure(yscrollcommand=scrollbar.set)

        # Log panel
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding="10")
        log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def start_analysis(self):
        num_instances = self.num_instances_var.get()

        if num_instances < 1:
            messagebox.showerror("Error", "Number of instances must be at least 1")
            return

        if num_instances > len(self.analysis_prompts):
            num_instances = len(self.analysis_prompts)
            self.log(f"Limiting to {num_instances} instances (max unique prompts)")

        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        # Clear previous results
        for item in self.instance_tree.get_children():
            self.instance_tree.delete(item)
        self.instances.clear()
        self.processes.clear()
        self.results.clear()
        self.token_usage.clear()

        self.log(f"Starting {num_instances} codex analysis instances...")

        # Create instances
        for i in range(num_instances):
            instance_id = f"instance_{i+1}"
            prompt = self.analysis_prompts[i % len(self.analysis_prompts)]

            instance_data = {
                'id': instance_id,
                'prompt': prompt,
                'status': 'Starting',
                'start_time': time.time(),
                'tokens': 0,
                'output_file': self.results_dir / f"{instance_id}.txt"
            }

            self.instances.append(instance_data)

            # Add to tree
            tree_id = self.instance_tree.insert("", tk.END, text=f"Instance {i+1}: {prompt[:60]}...",
                                               values=("Starting", "0", "0s", "Pending"))
            instance_data['tree_id'] = tree_id

        # Start instances in background thread
        threading.Thread(target=self.run_instances, daemon=True).start()

        # Start UI update thread
        threading.Thread(target=self.update_ui_loop, daemon=True).start()

    def run_instances(self):
        """Run all codex instances in background"""
        for instance in self.instances:
            if not self.is_running:
                break

            # Start instance
            thread = threading.Thread(target=self.run_single_instance,
                                     args=(instance,), daemon=True)
            thread.start()

            # Small delay to avoid overwhelming the system
            time.sleep(2)

    def run_single_instance(self, instance):
        """Run a single codex instance"""
        try:
            instance['status'] = 'Running'
            self.log(f"{instance['id']}: Starting analysis...")

            # Build command
            cmd = [
                "codex", "exec",
                "--dangerously-bypass-approvals-and-sandbox",
                "--skip-git-repo-check",
                "-C", str(self.working_dir),
                instance['prompt']
            ]

            # Run process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(self.working_dir)
            )

            self.processes[instance['id']] = process

            # Collect output
            output_lines = []
            for line in process.stdout:
                output_lines.append(line)

                # Extract token usage
                token_match = re.search(r'tokens used:\s*([\d,]+)', line)
                if token_match:
                    tokens = int(token_match.group(1).replace(',', ''))
                    instance['tokens'] = tokens
                    self.token_usage[instance['id']] = tokens

            # Wait for completion
            return_code = process.wait()

            # Save output
            with open(instance['output_file'], 'w', encoding='utf-8') as f:
                f.write(''.join(output_lines))

            # Update status
            if return_code == 0:
                instance['status'] = 'Completed'
                instance['result'] = 'Success'
                self.log(f"{instance['id']}: Completed successfully")
            else:
                instance['status'] = 'Error'
                instance['result'] = f'Exit code {return_code}'
                self.log(f"{instance['id']}: Failed with exit code {return_code}")

            self.results[instance['id']] = {
                'output': ''.join(output_lines),
                'status': instance['status'],
                'tokens': instance['tokens']
            }

        except Exception as e:
            instance['status'] = 'Error'
            instance['result'] = str(e)
            self.log(f"{instance['id']}: Error - {e}")

        finally:
            instance['end_time'] = time.time()

            # Check if all done
            self.check_all_complete()

    def update_ui_loop(self):
        """Periodically update UI with instance status"""
        while self.is_running:
            for instance in self.instances:
                runtime = time.time() - instance['start_time']
                runtime_str = f"{int(runtime)}s"

                if 'end_time' in instance:
                    runtime = instance['end_time'] - instance['start_time']
                    runtime_str = f"{int(runtime)}s"

                self.instance_tree.item(instance['tree_id'],
                                       values=(instance['status'],
                                              instance['tokens'],
                                              runtime_str,
                                              instance.get('result', 'Pending')))

            # Update progress
            completed = sum(1 for i in self.instances if i['status'] in ['Completed', 'Error'])
            total = len(self.instances)
            self.overall_progress['maximum'] = total
            self.overall_progress['value'] = completed
            self.progress_label.config(text=f"{completed}/{total} completed")

            time.sleep(1)

    def check_all_complete(self):
        """Check if all instances are done and create notification"""
        completed = sum(1 for i in self.instances if i['status'] in ['Completed', 'Error'])
        total = len(self.instances)

        if completed == total:
            self.log("=" * 60)
            self.log("ALL ANALYSIS INSTANCES COMPLETED!")
            self.log("=" * 60)

            # Generate consolidated report
            self.generate_consolidated_report()

            # Create notification marker for Claude
            notification_file = self.working_dir / "CODEX_ANALYSIS_COMPLETE.txt"
            with open(notification_file, 'w') as f:
                f.write(f"Codex Analysis Completed at {datetime.now()}\n")
                f.write(f"Total Instances: {total}\n")
                f.write(f"Successful: {sum(1 for i in self.instances if i['status'] == 'Completed')}\n")
                f.write(f"Failed: {sum(1 for i in self.instances if i['status'] == 'Error')}\n")
                f.write(f"\nConsolidated report: {self.results_dir / 'CONSOLIDATED_REPORT.txt'}\n")

            self.log(f"Notification file created: {notification_file}")

            # Update UI
            self.root.after(0, self.on_completion)

    def on_completion(self):
        """Called when all instances complete"""
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

        messagebox.showinfo("Analysis Complete",
                           "All codex instances have completed!\n\n"
                           "Consolidated report has been generated.\n"
                           "Claude Code will be notified.")

    def generate_consolidated_report(self):
        """Generate a consolidated analysis report"""
        report_file = self.results_dir / "CONSOLIDATED_REPORT.txt"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("FOCUSCHECK COMPREHENSIVE BUG ANALYSIS - CONSOLIDATED REPORT\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")

            # Summary
            f.write("SUMMARY\n")
            f.write("-"*80 + "\n")
            f.write(f"Total Instances: {len(self.instances)}\n")
            f.write(f"Successful: {sum(1 for i in self.instances if i['status'] == 'Completed')}\n")
            f.write(f"Failed: {sum(1 for i in self.instances if i['status'] == 'Error')}\n")
            f.write(f"Total Tokens Used: {sum(self.token_usage.values())}\n")
            f.write("\n")

            # Individual results
            f.write("DETAILED FINDINGS BY ANALYSIS AREA\n")
            f.write("="*80 + "\n\n")

            for idx, instance in enumerate(self.instances, 1):
                f.write(f"\n{'='*80}\n")
                f.write(f"INSTANCE {idx}: {instance['id']}\n")
                f.write(f"{'='*80}\n")
                f.write(f"Analysis Focus: {instance['prompt']}\n")
                f.write(f"Status: {instance['status']}\n")
                f.write(f"Tokens Used: {instance['tokens']}\n")

                if 'end_time' in instance:
                    runtime = instance['end_time'] - instance['start_time']
                    f.write(f"Runtime: {int(runtime)} seconds\n")

                f.write("\n")
                f.write("FINDINGS:\n")
                f.write("-"*80 + "\n")

                # Extract findings from output
                if instance['id'] in self.results:
                    output = self.results[instance['id']]['output']

                    # Try to extract key findings (look for common patterns)
                    findings = self.extract_findings(output)

                    if findings:
                        f.write(findings)
                    else:
                        f.write("(No specific findings extracted - see detailed output below)\n")

                    f.write("\n\nFULL OUTPUT:\n")
                    f.write("-"*80 + "\n")
                    f.write(output)
                else:
                    f.write("(No output captured)\n")

                f.write("\n")

        self.log(f"Consolidated report generated: {report_file}")

    def extract_findings(self, output):
        """Extract key findings from codex output"""
        findings = []

        # Look for common issue patterns
        bug_keywords = [
            'bug', 'error', 'issue', 'problem', 'vulnerability',
            'memory leak', 'race condition', 'deadlock',
            'incorrect', 'missing', 'undefined', 'null pointer',
            'exception', 'crash', 'fail'
        ]

        lines = output.split('\n')
        for i, line in enumerate(lines):
            line_lower = line.lower()

            # Check if line contains bug-related keywords
            if any(keyword in line_lower for keyword in bug_keywords):
                # Include context (line before and after)
                start = max(0, i-1)
                end = min(len(lines), i+2)
                context = '\n'.join(lines[start:end])
                findings.append(context + '\n')

        return '\n'.join(findings) if findings else ""

    def stop_analysis(self):
        """Stop all running instances"""
        self.is_running = False

        for instance_id, process in self.processes.items():
            try:
                process.terminate()
                self.log(f"{instance_id}: Terminated")
            except Exception as e:
                self.log(f"{instance_id}: Error terminating - {e}")

        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.log("Analysis stopped by user")

    def view_report(self):
        """Open the consolidated report in a new window"""
        report_file = self.results_dir / "CONSOLIDATED_REPORT.txt"

        if not report_file.exists():
            messagebox.showwarning("No Report", "Consolidated report not found. Run analysis first.")
            return

        # Create new window
        report_window = tk.Toplevel(self.root)
        report_window.title("Consolidated Analysis Report")
        report_window.geometry("1000x700")

        # Text widget with scrollbar
        frame = ttk.Frame(report_window, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        report_window.columnconfigure(0, weight=1)
        report_window.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        text = scrolledtext.ScrolledText(frame, wrap=tk.WORD)
        text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Load and display report
        with open(report_file, 'r', encoding='utf-8') as f:
            text.insert(tk.END, f.read())

        text.config(state=tk.DISABLED)

def main():
    root = tk.Tk()
    app = CodexAnalysisManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()
