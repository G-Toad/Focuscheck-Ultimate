//
//  NotificationManager.swift
//  FocusCheckiOS
//
//  Manages aggressive check-in notifications with escalation
//

import Foundation
import UserNotifications
import AVFoundation

class NotificationManager: NSObject, ObservableObject, UNUserNotificationCenterDelegate {
    static let shared = NotificationManager()

    @Published var pendingNotifications: [String] = []

    private var audioPlayer: AVAudioPlayer?

    override init() {
        super.init()
        UNUserNotificationCenter.current().delegate = self
    }

    // MARK: - Setup
    func setupNotificationCategories() {
        // Response actions for quick reply
        let focusedAction = UNNotificationAction(
            identifier: "FOCUSED_ACTION",
            title: "✅ I'm Focused",
            options: [.foreground]
        )

        let distractedAction = UNNotificationAction(
            identifier: "DISTRACTED_ACTION",
            title: "⚠️ Got Distracted",
            options: [.foreground]
        )

        let snoozeAction = UNNotificationAction(
            identifier: "SNOOZE_ACTION",
            title: "Snooze 5 min",
            options: []
        )

        // Check-in category
        let checkInCategory = UNNotificationCategory(
            identifier: "CHECK_IN",
            actions: [focusedAction, distractedAction, snoozeAction],
            intentIdentifiers: [],
            options: [.customDismissAction]
        )

        // Escalated category (fewer options, more urgent)
        let escalatedCategory = UNNotificationCategory(
            identifier: "CHECK_IN_ESCALATED",
            actions: [focusedAction, distractedAction],
            intentIdentifiers: [],
            options: []
        )

        UNUserNotificationCenter.current().setNotificationCategories([checkInCategory, escalatedCategory])
    }

    // MARK: - Scheduling
    func scheduleCheckIn(after seconds: TimeInterval, escalationLevel: Int = 0, appState: AppState) {
        // Don't schedule if paused
        guard !appState.isPaused else {
            print("⏸️  Paused - not scheduling notification")
            return
        }

        let content = UNMutableNotificationContent()

        // Customize based on escalation
        switch escalationLevel {
        case 0:
            content.title = "Quick Check-In"
            content.body = "Are you still focused on your work?"
            content.categoryIdentifier = "CHECK_IN"
            content.sound = .default

        case 1:
            content.title = "Focus Check"
            content.body = "You've been on YouTube for a while. Still productive?"
            content.categoryIdentifier = "CHECK_IN"
            content.sound = .defaultCritical
            content.interruptionLevel = .timeSensitive

        case 2:
            content.title = "⚠️ ATTENTION NEEDED"
            content.body = "3rd check - are you hypnotized by infinite scroll?"
            content.categoryIdentifier = "CHECK_IN_ESCALATED"
            content.sound = .defaultCritical
            content.interruptionLevel = .critical

        case 3:
            content.title = "🚨 WAKE UP"
            content.body = "You've ignored multiple prompts. Time wasted: \(appState.todayDistractionMinutes)min"
            content.categoryIdentifier = "CHECK_IN_ESCALATED"
            content.sound = .defaultCritical
            content.interruptionLevel = .critical

        default:
            content.title = "🚨🚨 SNAP OUT OF IT"
            content.body = "You're \(appState.todayDistractionMinutes) minutes deep. Break the trance NOW."
            content.categoryIdentifier = "CHECK_IN_ESCALATED"
            content.sound = .defaultCritical
            content.interruptionLevel = .critical
        }

        content.badge = NSNumber(value: escalationLevel + 1)

        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: seconds, repeats: false)
        let identifier = "check-in-\(UUID().uuidString)"
        let request = UNNotificationRequest(identifier: identifier, content: content, trigger: trigger)

        UNUserNotificationCenter.current().add(request) { error in
            if let error = error {
                print("❌ Error scheduling notification: \(error.localizedDescription)")
            } else {
                print("✅ Scheduled check-in in \(Int(seconds))s at level \(escalationLevel)")
            }
        }
    }

    // MARK: - Continuous Prompting During Distraction
    func startContinuousPrompting(appState: AppState) {
        // Clear any pending notifications first
        cancelAllNotifications()

        // Schedule first prompt after 2 minutes
        scheduleCheckIn(after: 120, escalationLevel: appState.escalationLevel, appState: appState)

        // Schedule follow-ups based on escalation level
        let interval = appState.checkInIntervalSeconds
        for i in 1...10 {
            let delay = 120 + (interval * TimeInterval(i))
            scheduleCheckIn(after: delay, escalationLevel: min(appState.escalationLevel + i/3, 5), appState: appState)
        }
    }

    func stopContinuousPrompting() {
        cancelAllNotifications()
    }

    func cancelAllNotifications() {
        UNUserNotificationCenter.current().removeAllPendingNotificationRequests()
        print("🗑️  Cancelled all pending notifications")
    }

    // MARK: - Delegate Methods
    func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification, withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        // Show notification even when app is in foreground
        completionHandler([.banner, .sound, .badge])
    }

    func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse, withCompletionHandler completionHandler: @escaping () -> Void) {
        handleNotificationResponse(response.actionIdentifier)
        completionHandler()
    }

    private func handleNotificationResponse(_ actionIdentifier: String) {
        switch actionIdentifier {
        case "FOCUSED_ACTION":
            print("✅ User reported: Focused")
            NotificationCenter.default.post(name: .userRespondedFocused, object: nil)

        case "DISTRACTED_ACTION":
            print("⚠️  User reported: Distracted")
            NotificationCenter.default.post(name: .userRespondedDistracted, object: nil)

        case "SNOOZE_ACTION":
            print("⏰ User snoozed for 5 minutes")
            NotificationCenter.default.post(name: .userSnoozed, object: nil)

        case UNNotificationDismissActionIdentifier:
            print("🔕 User dismissed notification (ignored)")
            NotificationCenter.default.post(name: .userIgnoredPrompt, object: nil)

        default:
            break
        }
    }
}

// MARK: - Notification Names
extension Notification.Name {
    static let userRespondedFocused = Notification.Name("userRespondedFocused")
    static let userRespondedDistracted = Notification.Name("userRespondedDistracted")
    static let userSnoozed = Notification.Name("userSnoozed")
    static let userIgnoredPrompt = Notification.Name("userIgnoredPrompt")
}
