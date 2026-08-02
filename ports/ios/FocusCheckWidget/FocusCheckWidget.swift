//
//  FocusCheckWidget.swift
//  FocusCheckWidget
//
//  Control Center widget for emergency pause access
//

import WidgetKit
import SwiftUI

struct FocusCheckWidget: Widget {
    let kind: String = "FocusCheckWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: Provider()) { entry in
            FocusCheckWidgetEntryView(entry: entry)
        }
        .configurationDisplayName("FocusCheck Control")
        .description("Quick access to pause monitoring for emergencies")
        .supportedFamilies([.systemSmall, .accessoryCircular, .accessoryRectangular])
    }
}

// MARK: - Provider
struct Provider: TimelineProvider {
    func placeholder(in context: Context) -> SimpleEntry {
        SimpleEntry(date: Date(), isPaused: false, minutesWasted: 0)
    }

    func getSnapshot(in context: Context, completion: @escaping (SimpleEntry) -> ()) {
        let isPaused = UserDefaults(suiteName: "group.com.focuscheck.shared")?.bool(forKey: "isPaused") ?? false
        let minutesWasted = UserDefaults(suiteName: "group.com.focuscheck.shared")?.integer(forKey: "todayDistractionMinutes") ?? 0
        let entry = SimpleEntry(date: Date(), isPaused: isPaused, minutesWasted: minutesWasted)
        completion(entry)
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<Entry>) -> ()) {
        let isPaused = UserDefaults(suiteName: "group.com.focuscheck.shared")?.bool(forKey: "isPaused") ?? false
        let minutesWasted = UserDefaults(suiteName: "group.com.focuscheck.shared")?.integer(forKey: "todayDistractionMinutes") ?? 0

        let entry = SimpleEntry(date: Date(), isPaused: isPaused, minutesWasted: minutesWasted)

        // Update every minute
        let nextUpdate = Calendar.current.date(byAdding: .minute, value: 1, to: Date())!
        let timeline = Timeline(entries: [entry], policy: .after(nextUpdate))
        completion(timeline)
    }
}

struct SimpleEntry: TimelineEntry {
    let date: Date
    let isPaused: Bool
    let minutesWasted: Int
}

// MARK: - Widget Views
struct FocusCheckWidgetEntryView: View {
    @Environment(\.widgetFamily) var family
    var entry: Provider.Entry

    var body: some View {
        switch family {
        case .systemSmall:
            SmallWidgetView(entry: entry)
        case .accessoryCircular:
            CircularWidgetView(entry: entry)
        case .accessoryRectangular:
            RectangularWidgetView(entry: entry)
        default:
            SmallWidgetView(entry: entry)
        }
    }
}

// MARK: - Small Widget (Home Screen)
struct SmallWidgetView: View {
    let entry: SimpleEntry

    var body: some View {
        ZStack {
            LinearGradient(
                colors: entry.isPaused ? [Color.orange, Color.orange.opacity(0.7)] : [Color.blue, Color.blue.opacity(0.7)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            VStack(spacing: 8) {
                Image(systemName: entry.isPaused ? "pause.circle.fill" : "eye.fill")
                    .font(.system(size: 32))
                    .foregroundColor(.white)

                Text(entry.isPaused ? "PAUSED" : "Monitoring")
                    .font(.headline)
                    .fontWeight(.bold)
                    .foregroundColor(.white)

                if !entry.isPaused && entry.minutesWasted > 0 {
                    Text("\(entry.minutesWasted)min wasted")
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.8))
                }

                Spacer()

                Text(entry.isPaused ? "Tap to Resume" : "Tap to Pause")
                    .font(.caption2)
                    .foregroundColor(.white.opacity(0.7))
            }
            .padding()
        }
        .widgetURL(URL(string: "focuscheck://toggle-pause"))
    }
}

// MARK: - Circular Widget (Lock Screen / Dynamic Island)
struct CircularWidgetView: View {
    let entry: SimpleEntry

    var body: some View {
        ZStack {
            AccessoryWidgetBackground()

            VStack(spacing: 2) {
                Image(systemName: entry.isPaused ? "pause.fill" : "eye.fill")
                    .font(.title3)

                if !entry.isPaused && entry.minutesWasted > 0 {
                    Text("\(entry.minutesWasted)")
                        .font(.caption2)
                        .fontWeight(.bold)
                }
            }
        }
        .widgetURL(URL(string: "focuscheck://toggle-pause"))
    }
}

// MARK: - Rectangular Widget (Lock Screen)
struct RectangularWidgetView: View {
    let entry: SimpleEntry

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: entry.isPaused ? "pause.circle.fill" : "eye.circle.fill")
                .font(.title2)

            VStack(alignment: .leading, spacing: 2) {
                Text(entry.isPaused ? "PAUSED" : "Monitoring")
                    .font(.headline)
                    .fontWeight(.bold)

                if !entry.isPaused && entry.minutesWasted > 0 {
                    Text("\(entry.minutesWasted) min wasted today")
                        .font(.caption2)
                }
            }

            Spacer()
        }
        .widgetURL(URL(string: "focuscheck://toggle-pause"))
    }
}

// MARK: - Preview
struct FocusCheckWidget_Previews: PreviewProvider {
    static var previews: some View {
        FocusCheckWidgetEntryView(entry: SimpleEntry(date: Date(), isPaused: false, minutesWasted: 23))
            .previewContext(WidgetPreviewContext(family: .systemSmall))

        FocusCheckWidgetEntryView(entry: SimpleEntry(date: Date(), isPaused: true, minutesWasted: 0))
            .previewContext(WidgetPreviewContext(family: .accessoryCircular))

        FocusCheckWidgetEntryView(entry: SimpleEntry(date: Date(), isPaused: false, minutesWasted: 45))
            .previewContext(WidgetPreviewContext(family: .accessoryRectangular))
    }
}
