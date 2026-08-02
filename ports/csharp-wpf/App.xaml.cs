using System.Windows;
using FocusCheck.Wpf.Models;
using FocusCheck.Wpf.Services;

namespace FocusCheck.Wpf;

public partial class App : Application
{
    public SettingsModel Settings { get; private set; } = SettingsModel.CreateDefault();
    public SettingsStore SettingsStore { get; private set; } = new SettingsStore();

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        Settings = SettingsStore.Load();
    }
}
