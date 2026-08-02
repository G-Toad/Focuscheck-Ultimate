using System;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;
using FocusCheck.Wpf.Models;

namespace FocusCheck.Wpf.Services;

public class SettingsStore
{
    private readonly string _path;
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    public SettingsStore(string? customPath = null)
    {
        _path = customPath ?? GetDefaultPath();
        Directory.CreateDirectory(Path.GetDirectoryName(_path)!);
    }

    public SettingsModel Load()
    {
        try
        {
            if (File.Exists(_path))
            {
                var json = File.ReadAllText(_path);
                var model = JsonSerializer.Deserialize<SettingsModel>(json, JsonOptions);
                if (model != null) return model;
            }
        }
        catch
        {
            // Fall back to defaults
        }
        return SettingsModel.CreateDefault();
    }

    public void Save(SettingsModel settings)
    {
        var json = JsonSerializer.Serialize(settings, JsonOptions);
        File.WriteAllText(_path, json);
    }

    private static string GetDefaultPath()
    {
        var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        return Path.Combine(appData, "FocusCheck", "settings.json");
    }
}
