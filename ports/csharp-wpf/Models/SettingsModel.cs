using System.Collections.Generic;

namespace FocusCheck.Wpf.Models;

public class SettingsModel
{
    // Core timers
    public int IntervalSeconds { get; set; } = 60;
    public bool AlwaysOnTop { get; set; } = true;

    // Prompts
    public bool HideWastingButton { get; set; } = false;
    public bool FocusPromptAskDoing { get; set; } = true;
    public bool FocusPromptAskBenefits { get; set; } = true;
    public bool WastingPromptAskWhat { get; set; } = true;
    public bool WastingPromptAskConsequences { get; set; } = true;

    // Challenges
    public bool ChallengeSystemEnabled { get; set; } = true;
    public double ChallengeStudyingFrequency { get; set; } = 0.3;
    public double ChallengeWastingFrequency { get; set; } = 0.5;
    public int ChallengeMinWords { get; set; } = 3;
    public int ChallengeMinTotalLength { get; set; } = 10;

    // Camera
    public bool CameraFeedEnabled { get; set; } = false;
    public string CameraSizingMode { get; set; } = "aspect_ratio"; // aspect_ratio | fixed_size | face_tracking | manual_crop
    public int CameraFeedWidth { get; set; } = 320;
    public int CameraFeedHeight { get; set; } = 240;
    public bool CameraFlipHorizontal { get; set; } = true;

    // Misc
    public bool ModalDialogAutoFocus { get; set; } = true;

    public static SettingsModel CreateDefault() => new();
}
