# Manual Repro Checklist

This document outlines the steps to manually reproduce potential bugs in FocusCheck.

**Instructions:**

1.  Enable Doctor Mode by setting the environment variable `FOCUSCHECK_DOCTOR=1`.
2.  Start the application.
3.  Follow the steps below and observe the logs for any anomalies.

**Checklist:**

1.  **Prompt now:**
    - Action: Right-click the tray icon and select "Prompt now".
    - Log Marker: `=== REPRO STEP: Prompt now ===`
    - Expected: A prompt dialog should appear.

2.  **Trigger intervention:**
    - Action: Answer "yes" to the intervention prompt, select a window, and let the spotlight appear.
    - Log Marker: `=== REPRO STEP: Trigger intervention ===`
    - Expected: The spotlight overlay should appear, and the intervention dialog should be shown.

3.  **Cancel at selection stage:**
    - Action: Trigger an intervention, and click "Cancel" in the window selection dialog.
    - Log Marker: `=== REPRO STEP: Cancel at selection stage ===`
    - Expected: The intervention should be aborted, and the main prompt should be restored.

4.  **Cancel at spotlight stage:**
    - Action: Trigger an intervention, proceed to the spotlight stage, and click "Cancel" in the intervention dialog.
    - Log Marker: `=== REPRO STEP: Cancel at spotlight stage ===`
    - Expected: The intervention should be aborted, and the main prompt should be restored.

5.  **Toggle V2 engine:**
    - Action: Go to settings, toggle the "Monitoring Engine" to "V2", save, and then toggle it back to "V1".
    - Log Marker: `=== REPRO STEP: Toggle V2 engine ===`
    - Expected: The application should switch the monitoring engine without errors.

6.  **Toggle spam detection:**
    - Action: Go to settings, disable "Enable spam detection", save, and trigger a prompt. Enter a spammy answer. Then, enable it and repeat.
    - Log Marker: `=== REPRO STEP: Toggle spam detection ===`
    - Expected: When disabled, no spam checks should be performed. When enabled, spam checks should be performed.

7.  **Overlay gate manual config:**
    - Action: Stop the app, edit the settings file to set `"overlays_enabled": false`, restart, and trigger an intervention.
    - Log Marker: `=== REPRO STEP: Toggle overlays ===`
    - Expected: No overlays (blackout, spotlight) should be shown during the intervention. This is an internal gate, not a normal Settings UI toggle.

8.  **Toggle tray button disable:**
    - Action: Go to settings, disable "Enable exit button", and then try to exit the application from the tray menu.
    - Log Marker: `=== REPRO STEP: Toggle tray button disable ===`
    - Expected: The "Exit" button in the tray menu should be disabled.
