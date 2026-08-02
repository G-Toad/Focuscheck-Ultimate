using System.Windows;
using FocusCheck.Wpf.Models;
using FocusCheck.Wpf.Services;

namespace FocusCheck.Wpf;

public partial class MainWindow : Window
{
    private readonly SettingsModel _settings;
    private readonly SettingsStore _store;

    public MainWindow()
    {
        InitializeComponent();
        var app = (App)Application.Current;
        _settings = app.Settings;
        _store = app.SettingsStore;
    }

    private void OpenPrompt(object sender, RoutedEventArgs e)
    {
        new PromptWindow(_settings).ShowDialog();
    }

    private void OpenSettings(object sender, RoutedEventArgs e)
    {
        var win = new SettingsWindow(_settings, _store);
        win.ShowDialog();
    }

    private void OpenCameraPreview(object sender, RoutedEventArgs e)
    {
        var win = new CameraPreviewWindow();
        win.Show();
    }
}
