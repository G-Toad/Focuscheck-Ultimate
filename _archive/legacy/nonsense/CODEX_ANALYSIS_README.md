# Codex Analysis Manager - User Guide

## Overview
This system runs multiple parallel codex instances to perform comprehensive bug analysis on the FocusCheck application.

## Files Created
1. **codex_analysis_manager.py** - Main GUI application for managing analysis
2. **monitor_codex_completion.py** - Monitor script for detecting completion
3. **codex_analysis_results/** - Directory where all results are stored

## How to Use

### Step 1: Launch the Manager GUI
```bash
python codex_analysis_manager.py
```

### Step 2: Configure and Start Analysis
1. Set the number of instances (default: 10, max: 20 unique analyses)
2. Click "Start Analysis"
3. The GUI will show real-time progress for each instance
4. You can minimize the window and let it run in the background

### Step 3: Monitor Progress
The GUI shows:
- **Overall Progress Bar** - Total completion percentage
- **Instance List** - Status of each instance including:
  - Current status (Starting, Running, Completed, Error)
  - Tokens used
  - Runtime
  - Result summary
- **Activity Log** - Real-time event log

### Step 4: Wait for Completion
When all instances complete:
- A notification popup will appear
- A file `CODEX_ANALYSIS_COMPLETE.txt` will be created
- A consolidated report will be generated
- Claude Code will be automatically notified

### Step 5: Review Results
Click "View Consolidated Report" to see:
- Summary of all findings
- Issues organized by analysis area
- Token usage statistics
- Detailed output from each instance

## Analysis Areas Covered

The system runs specialized analyses for:

1. **Import & Module Issues** - Import errors, circular dependencies
2. **Threading Issues** - Race conditions, deadlocks, resource cleanup
3. **Settings & Configuration** - Validation errors, data persistence
4. **GUI Bugs** - Event handling, memory leaks, UI issues
5. **Database Issues** - SQL problems, transaction bugs, data integrity
6. **Utility Functions** - Error handling, edge cases
7. **Platform-Specific** - Windows API bugs, registry issues
8. **Exception Handling** - Uncaught errors, error recovery
9. **Resource Leaks** - File handles, database connections, memory
10. **Concurrency** - Multi-threading bugs, synchronization
11. **Input Validation** - Boundary conditions, edge cases
12. **Logic Errors** - Algorithm bugs, calculation mistakes
13. **Code Quality** - Code smells, refactoring opportunities
14. **UI Dialogs** - Dialog-specific bugs
15. **Audio System** - Audio playback and device issues
16. **System Tray** - Notification and menu bugs
17. **Pause Guard** - Auto-pause detection issues
18. **Task Database** - CRUD operations and queries
19. **CSV Logging** - File handling and data corruption
20. **Security** - Comprehensive security audit

## Output Files

All results are saved in `codex_analysis_results/`:
- `instance_1.txt` through `instance_N.txt` - Individual instance outputs
- `CONSOLIDATED_REPORT.txt` - Complete analysis report with all findings

## Features

### Token Usage Tracking
- Real-time token usage display for each instance
- Total token usage in consolidated report
- Helps monitor API costs

### Error Detection
- Automatically detects failed instances
- Captures error messages
- Includes in consolidated report

### Background Execution
- Runs independently from Claude Code
- Can minimize and continue working
- Notification when complete

### Progress Monitoring
- Visual progress bar
- Per-instance status updates
- Runtime tracking

## Stopping Analysis

If you need to stop the analysis:
1. Click "Stop All" button
2. All running instances will be terminated
3. Partial results will be saved

## Troubleshooting

### "Codex not found" error
Make sure codex CLI is installed and in PATH:
```bash
codex --version
```

### Instances failing immediately
- Check codex login: `codex login`
- Verify working directory is correct
- Check codex_analysis_results folder permissions

### High token usage warning
- Each instance can use 50K-150K tokens
- 10 instances ≈ 500K-1.5M tokens
- Adjust number of instances accordingly

## After Completion

When you see the completion notification:
1. Open the consolidated report
2. Review all findings
3. Claude Code will help implement fixes based on the report

## Tips

- **Start small**: Try 5-10 instances first to gauge token usage
- **Monitor progress**: Keep GUI open to watch for issues
- **Check individual outputs**: If an instance finds critical bugs, review its detailed output
- **Save reports**: Reports are timestamped, keep them for reference

## Notification System

The system creates two notification files when complete:
1. `CODEX_ANALYSIS_COMPLETE.txt` - Completion summary
2. `ALERT_CLAUDE_CODE.txt` - Claude Code trigger file

These files signal that analysis is done and results are ready for review.
