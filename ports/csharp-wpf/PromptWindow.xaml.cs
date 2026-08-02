using System.Windows;
using FocusCheck.Wpf.Models;

namespace FocusCheck.Wpf;

public partial class PromptWindow : Window
{
    private readonly SettingsModel _settings;

    public PromptWindow(SettingsModel settings)
    {
        _settings = settings;
        InitializeComponent();
    }
}
