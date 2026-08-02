//
//  ActivityMonitorManager.swift
//  FocusCheckiOS
//
//  Uses Screen Time API to detect YouTube/browser usage and trigger interventions
//

import Foundation
import FamilyControls
import DeviceActivity
import ManagedSettings

class ActivityMonitorManager: ObservableObject {
    @Published var isMonitoring = false
    @Published var detectedDistractionApp: String?

    private let store = ManagedSettingsStore()
    private let center = AuthorizationCenter.shared

    // MARK: - Start/Stop Monitoring
    func startMonitoring() {
        guard center.authorizationStatus == .approved else {
            print("❌ Screen Time authorization not granted")
            return
        }

        isMonitoring = true
        setupActivityMonitoring()
        print("✅ Started monitoring for distracting apps")
    }

    func stopMonitoring() {
        isMonitoring = false
        DeviceActivityCenter().stopMonitoring()
        print("⏹️  Stopped monitoring")
    }

    private func setupActivityMonitoring() {
        // Create a DeviceActivityMonitor to track app usage
        let schedule = DeviceActivitySchedule(
            intervalStart: DateComponents(hour: 0, minute: 0),
            intervalEnd: DateComponents(hour: 23, minute: 59),
            repeats: true
        )

        let activityName = DeviceActivityName("focuscheck.monitoring")

        do {
            try DeviceActivityCenter().startMonitoring(activityName, during: schedule)
            print("✅ DeviceActivity monitoring started")
        } catch {
            print("❌ Failed to start monitoring: \(error)")
        }
    }

    // MARK: - Shield Configuration
    func enableShieldForDistractionApps(appTokens: Set<ApplicationToken>) {
        // Shield the specified apps
        store.shield.applications = appTokens.isEmpty ? nil : appTokens

        // Configure shield appearance
        store.shield.applicationCategories = nil
    }

    func disableShield() {
        store.shield.applications = nil
        store.shield.applicationCategories = nil
    }

    // MARK: - App Detection
    func checkForDistractionApps() {
        // This would typically be called by DeviceActivityMonitor extension
        // For now, we'll use a simplified check

        // Note: Actual app detection happens in DeviceActivityMonitor extension
        // which we'll create separately
        print("🔍 Checking for distraction app usage...")
    }
}

// MARK: - DeviceActivityMonitor Extension
// Note: This needs to be in a separate extension target
// Create a new "Device Activity Monitor Extension" in Xcode

/*
 In DeviceActivityMonitor.swift (extension):

 import DeviceActivity
 import Foundation

 class DeviceActivityMonitor: DeviceActivityMonitor {
     override func intervalDidStart(for activity: DeviceActivityName) {
         super.intervalDidStart(for: activity)
         // Notify main app that monitoring started
     }

     override func intervalDidEnd(for activity: DeviceActivityName) {
         super.intervalDidEnd(for: activity)
         // Notify main app that monitoring ended
     }

     // Called when user opens a monitored app
     override func eventDidReachThreshold(_ event: DeviceActivityEvent.Name, activity: DeviceActivityName) {
         super.eventDidReachThreshold(event, activity: activity)

         // Post notification to main app
         let userInfo = ["eventName": event.rawValue, "timestamp": Date()]
         NotificationCenter.default.post(name: .distractingAppOpened, object: nil, userInfo: userInfo)

         // Trigger check-in notification
         scheduleImmediateCheckIn()
     }

     private func scheduleImmediateCheckIn() {
         let content = UNMutableNotificationContent()
         content.title = "🎯 Focus Check"
         content.body = "You just opened a distracting app. Are you doing this intentionally?"
         content.sound = .defaultCritical
         content.interruptionLevel = .timeSensitive

         let trigger = UNTimeIntervalNotificationTrigger(timeInterval: 1, repeats: false)
         let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: trigger)

         UNUserNotificationCenter.current().add(request)
     }
 }
 */

extension Notification.Name {
    static let distractingAppOpened = Notification.Name("distractingAppOpened")
}
