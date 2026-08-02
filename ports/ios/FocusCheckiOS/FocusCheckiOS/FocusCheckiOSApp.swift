//
//  FocusCheckiOSApp.swift
//  FocusCheckiOS
//
//  Main entry point for the FocusCheck iOS app
//

import SwiftUI
import UserNotifications
import FamilyControls

@main
struct FocusCheckiOSApp: App {
    @StateObject private var appState = AppState()
    @StateObject private var notificationManager = NotificationManager()
    @StateObject private var monitorManager = ActivityMonitorManager()

    init() {
        // Request notification permissions on launch
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge, .criticalAlert]) { granted, error in
            if granted {
                print("✅ Notification permissions granted")
            } else if let error = error {
                print("❌ Notification error: \(error.localizedDescription)")
            }
        }

        // Request Screen Time permissions
        AuthorizationCenter.shared.requestAuthorization { result in
            switch result {
            case .success:
                print("✅ Screen Time permissions granted")
            case .failure(let error):
                print("❌ Screen Time error: \(error.localizedDescription)")
            }
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .environmentObject(notificationManager)
                .environmentObject(monitorManager)
                .onAppear {
                    notificationManager.setupNotificationCategories()
                    if appState.isMonitoringEnabled && !appState.isPaused {
                        monitorManager.startMonitoring()
                    }
                }
        }
    }
}
