//
//  DeepLinkHandler.swift
//  FocusCheckiOS
//
//  Handles deep links from widgets and shortcuts
//

import SwiftUI

class DeepLinkHandler: ObservableObject {
    @Published var activeLink: DeepLink?

    enum DeepLink: String {
        case togglePause = "toggle-pause"
        case checkIn = "check-in"
        case openStats = "stats"
    }

    func handle(url: URL, appState: AppState, notificationManager: NotificationManager, monitorManager: ActivityMonitorManager) {
        guard url.scheme == "focuscheck" else { return }

        let path = url.host ?? ""

        switch path {
        case "toggle-pause":
            handleTogglePause(appState: appState, notificationManager: notificationManager, monitorManager: monitorManager)

        case "check-in":
            activeLink = .checkIn

        case "stats":
            activeLink = .openStats

        default:
            print("Unknown deep link: \(path)")
        }
    }

    private func handleTogglePause(appState: AppState, notificationManager: NotificationManager, monitorManager: ActivityMonitorManager) {
        appState.isPaused.toggle()

        if appState.isPaused {
            notificationManager.cancelAllNotifications()
            monitorManager.stopMonitoring()

            // Sync to widget
            UserDefaults(suiteName: "group.com.focuscheck.shared")?.set(true, forKey: "isPaused")
        } else {
            if appState.isMonitoringEnabled {
                monitorManager.startMonitoring()
            }

            // Sync to widget
            UserDefaults(suiteName: "group.com.focuscheck.shared")?.set(false, forKey: "isPaused")
        }

        print("🔄 Toggled pause: \(appState.isPaused)")
    }
}

// Update ContentView to handle deep links
extension ContentView {
    func handleDeepLink(_ url: URL) {
        let handler = DeepLinkHandler()
        handler.handle(url: url, appState: appState, notificationManager: notificationManager, monitorManager: monitorManager)
    }
}
