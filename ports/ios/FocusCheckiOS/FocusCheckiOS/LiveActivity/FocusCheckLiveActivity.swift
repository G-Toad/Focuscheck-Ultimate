//
//  FocusCheckLiveActivity.swift
//  FocusCheckiOS
//
//  Live Activity for persistent countdown display on lock screen and Dynamic Island
//

import ActivityKit
import WidgetKit
import SwiftUI

// MARK: - Activity Attributes
struct FocusCheckAttributes: ActivityAttributes {
    public struct ContentState: Codable, Hashable {
        var nextCheckInTime: Date
        var distractionMinutes: Int
        var escalationLevel: Int
        var isPaused: Bool
    }

    // Fixed attributes (don't change during activity)
    var startTime: Date
}

// MARK: - Live Activity Widget
@available(iOS 16.1, *)
struct FocusCheckLiveActivity: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: FocusCheckAttributes.self) { context in
            // Lock Screen UI
            LockScreenLiveActivityView(context: context)
        } dynamicIsland: { context in
            DynamicIsland {
                // Expanded view
                DynamicIslandExpandedRegion(.leading) {
                    HStack(spacing: 8) {
                        Image(systemName: context.state.isPaused ? "pause.circle.fill" : "eye.circle.fill")
                            .font(.title2)
                            .foregroundColor(context.state.isPaused ? .orange : .blue)

                        VStack(alignment: .leading, spacing: 2) {
                            Text(context.state.isPaused ? "Paused" : "Monitoring")
                                .font(.caption)
                                .fontWeight(.bold)

                            if context.state.escalationLevel > 0 {
                                Text("Level \(context.state.escalationLevel)")
                                    .font(.caption2)
                                    .foregroundColor(.red)
                            }
                        }
                    }
                }

                DynamicIslandExpandedRegion(.trailing) {
                    if !context.state.isPaused {
                        VStack(alignment: .trailing, spacing: 4) {
                            Text("Next Check:")
                                .font(.caption2)
                                .foregroundColor(.gray)

                            Text(context.state.nextCheckInTime, style: .relative)
                                .font(.caption)
                                .fontWeight(.bold)
                                .monospacedDigit()
                        }
                    }
                }

                DynamicIslandExpandedRegion(.center) {
                    if context.state.distractionMinutes > 0 {
                        VStack(spacing: 4) {
                            Text("\(context.state.distractionMinutes)")
                                .font(.title)
                                .fontWeight(.bold)
                                .foregroundColor(.orange)

                            Text("minutes wasted")
                                .font(.caption2)
                                .foregroundColor(.gray)
                        }
                        .padding(.vertical, 8)
                    }
                }

                DynamicIslandExpandedRegion(.bottom) {
                    HStack(spacing: 16) {
                        Button(intent: TogglePauseIntent()) {
                            Label(context.state.isPaused ? "Resume" : "Pause", systemImage: context.state.isPaused ? "play.fill" : "pause.fill")
                                .font(.caption)
                        }
                        .tint(context.state.isPaused ? .green : .orange)

                        Button(intent: TriggerCheckInIntent()) {
                            Label("Check In Now", systemImage: "checkmark.circle.fill")
                                .font(.caption)
                        }
                        .tint(.blue)
                    }
                }
            } compactLeading: {
                // Compact leading (left side of notch)
                Image(systemName: context.state.isPaused ? "pause.fill" : "eye.fill")
                    .foregroundColor(context.state.isPaused ? .orange : .blue)
            } compactTrailing: {
                // Compact trailing (right side of notch)
                if !context.state.isPaused {
                    Text(context.state.nextCheckInTime, style: .relative)
                        .font(.caption2)
                        .fontWeight(.bold)
                        .monospacedDigit()
                        .frame(width: 50)
                } else {
                    Image(systemName: "pause.fill")
                        .foregroundColor(.orange)
                }
            } minimal: {
                // Minimal (when multiple activities are active)
                Image(systemName: context.state.escalationLevel > 2 ? "exclamationmark.triangle.fill" : "eye.fill")
                    .foregroundColor(context.state.escalationLevel > 2 ? .red : .blue)
            }
        }
    }
}

// MARK: - Lock Screen View
struct LockScreenLiveActivityView: View {
    let context: ActivityViewContext<FocusCheckAttributes>

    var body: some View {
        HStack(spacing: 16) {
            // Icon
            Image(systemName: context.state.isPaused ? "pause.circle.fill" : "eye.circle.fill")
                .font(.title)
                .foregroundColor(context.state.isPaused ? .orange : .blue)

            VStack(alignment: .leading, spacing: 4) {
                // Status
                Text(context.state.isPaused ? "FocusCheck Paused" : "FocusCheck Monitoring")
                    .font(.headline)
                    .fontWeight(.bold)

                // Next check-in or pause info
                if !context.state.isPaused {
                    HStack(spacing: 4) {
                        Text("Next check:")
                        Text(context.state.nextCheckInTime, style: .relative)
                            .fontWeight(.bold)
                            .monospacedDigit()
                    }
                    .font(.caption)
                    .foregroundColor(.secondary)
                } else {
                    Text("Monitoring paused")
                        .font(.caption)
                        .foregroundColor(.orange)
                }
            }

            Spacer()

            // Stats
            if context.state.distractionMinutes > 0 {
                VStack(spacing: 2) {
                    Text("\(context.state.distractionMinutes)")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.orange)

                    Text("min")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
            }

            // Escalation indicator
            if context.state.escalationLevel > 0 {
                VStack(spacing: 2) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.title3)
                        .foregroundColor(.red)

                    Text("L\(context.state.escalationLevel)")
                        .font(.caption2)
                        .fontWeight(.bold)
                        .foregroundColor(.red)
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
    }
}

// MARK: - App Intents for Live Activity
struct TogglePauseIntent: AppIntent {
    static var title: LocalizedStringResource = "Toggle Pause"

    func perform() async throws -> some IntentResult {
        // Toggle pause state
        let isPaused = UserDefaults(suiteName: "group.com.focuscheck.shared")?.bool(forKey: "isPaused") ?? false
        UserDefaults(suiteName: "group.com.focuscheck.shared")?.set(!isPaused, forKey: "isPaused")

        // Post notification to main app
        NotificationCenter.default.post(name: .togglePauseFromLiveActivity, object: nil)

        return .result()
    }
}

struct TriggerCheckInIntent: AppIntent {
    static var title: LocalizedStringResource = "Trigger Check-In"

    func perform() async throws -> some IntentResult {
        // Post notification to main app to show check-in
        NotificationCenter.default.post(name: .triggerCheckInFromLiveActivity, object: nil)

        return .result()
    }
}

extension Notification.Name {
    static let togglePauseFromLiveActivity = Notification.Name("togglePauseFromLiveActivity")
    static let triggerCheckInFromLiveActivity = Notification.Name("triggerCheckInFromLiveActivity")
}

// MARK: - Live Activity Manager
@available(iOS 16.1, *)
class LiveActivityManager: ObservableObject {
    @Published var currentActivity: Activity<FocusCheckAttributes>?

    func startActivity(nextCheckIn: Date, distractionMinutes: Int, escalationLevel: Int, isPaused: Bool) {
        // End existing activity if any
        endActivity()

        let attributes = FocusCheckAttributes(startTime: Date())
        let contentState = FocusCheckAttributes.ContentState(
            nextCheckInTime: nextCheckIn,
            distractionMinutes: distractionMinutes,
            escalationLevel: escalationLevel,
            isPaused: isPaused
        )

        do {
            let activity = try Activity<FocusCheckAttributes>.request(
                attributes: attributes,
                contentState: contentState,
                pushType: nil
            )
            currentActivity = activity
            print("✅ Live Activity started")
        } catch {
            print("❌ Failed to start Live Activity: \(error)")
        }
    }

    func updateActivity(nextCheckIn: Date, distractionMinutes: Int, escalationLevel: Int, isPaused: Bool) {
        guard let activity = currentActivity else { return }

        let contentState = FocusCheckAttributes.ContentState(
            nextCheckInTime: nextCheckIn,
            distractionMinutes: distractionMinutes,
            escalationLevel: escalationLevel,
            isPaused: isPaused
        )

        Task {
            await activity.update(using: contentState)
            print("🔄 Live Activity updated")
        }
    }

    func endActivity() {
        guard let activity = currentActivity else { return }

        Task {
            await activity.end(dismissalPolicy: .immediate)
            currentActivity = nil
            print("🛑 Live Activity ended")
        }
    }
}
