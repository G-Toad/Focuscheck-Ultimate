# FocusCheck WPF Port (C#/.NET)

This is a scaffold to migrate the Python/Tk FocusCheck into a native Windows WPF app.

## Structure
- FocusCheck.Wpf.csproj – .NET 8.0 Windows WPF project.
- App.xaml / App.xaml.cs – app entry.
- MainWindow – launcher (opens prompt, settings, camera preview).
- PromptWindow – placeholder for check-in dialog UI.
- SettingsWindow – tabs for general/challenges/camera placeholders.
- CameraPreviewWindow – placeholder for OpenCV/MediaCapture preview.
- Models/SettingsModel.cs – initial settings POCO (mirrors a subset of Python defaults).
- Services/SettingsStore.cs – JSON load/save for settings.

## Porting Plan (map from Python)
1) Settings model: expand SettingsModel to cover all keys in settings/defaults.py; wire validation/defaults.
2) Prompt dialog: port layout/logic from ui/dialogs/prompt_dialog.py and mixins. Map intensification/overdrive to WPF animations + Win32 P/Invoke.
3) Challenges & spam detection: reimplement ui/dialogs/challenge_system.py and ui/dialogs/spam_detection.py in C# classes, inject into PromptWindow.
4) Camera feed: use OpenCvSharp or MediaCapture; port manual crop/face tracking logic from ui/dialogs/prompt_dialog_mixins/camera_feed.py helpers.
5) Overdrive dimming: use layered windows / magnifier APIs (P/Invoke) to replicate stage-5 overlays.
6) Settings UI: bind to settings model; add tabs for prompts/challenges/camera; wire save/apply.
7) Tray integration: add NotifyIcon / Hwnd to show/hide prompts.

Build tip: install .NET SDK locally, then run dotnet build inside focuscheck-csharp. Incrementally port features following the plan above.
