using System.Windows;
using FocusCheck.Wpf.Models;
using FocusCheck.Wpf.Services;

namespace FocusCheck.Wpf;

public partial class SettingsWindow : Window
{
    private readonly SettingsModel _settings;
    private readonly SettingsStore _store;

    public SettingsWindow(SettingsModel settings, SettingsStore store)
    {
        _settings = settings;
        _store = store;
        InitializeComponent();
        DataContext = _settings;
    }

    private void OpenCameraPreview(object sender, RoutedEventArgs e)
    {
        var win = new CameraPreviewWindow();
        win.Show();
    }

    private void Save(object sender, RoutedEventArgs e)
    {
        _store.Save(_settings);
        MessageBox.Show(this, "Settings saved.", "Saved", MessageBoxButton.OK, MessageBoxImage.Information);
    }
}
