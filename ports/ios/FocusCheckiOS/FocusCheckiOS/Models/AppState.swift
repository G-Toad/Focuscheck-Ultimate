//
//  AppState.swift
//  FocusCheckiOS
//
//  Tracks app state including pause, monitoring, and usage stats
//

import SwiftUI
import Combine

class AppState: ObservableObject {
    // MARK: - Core State
    @Published var isPaused: Bool = false {
        didSet {
            UserDefaults.standard.set(isPaused, forKey: "isPaused")
            if isPaused {
                pausedAt = Date()
            } else {
                pausedAt = nil
            }
        }
    }

    @Published var isMonitoringEnabled: Bool = true {
        didSet {
            UserDefaults.standard.set(isMonitoringEnabled, forKey: "isMonitoringEnabled")
        }
    }

    @Published var pausedAt: Date?

    // MARK: - Distraction Tracking
    @Published var distractingAppsBlockList: Set<String> = ["com.google.ios.youtube", "com.brave.ios.browser"]
    @Published var currentlyInDistractingApp: Bool = false
    @Published var distractingAppSessionStart: Date?
    @Published var todayDistractionMinutes: Int = 0
    @Published var ignoredPromptsCount: Int = 0

    // MARK: - Check-in State
    @Published var lastCheckInTime: Date?
    @Published var nextCheckInTime: Date?
    @Published var checkInIntervalSeconds: TimeInterval = 180 // 3 minutes default

    // MARK: - Escalation
    @Published var escalationLevel: Int = 0 {
        didSet {
            // As escalation increases, check-ins get more frequent
            updateCheckInInterval()
        }
    }

    init() {
        // Load persisted state
        isPaused = UserDefaults.standard.bool(forKey: "isPaused")
        isMonitoringEnabled = UserDefaults.standard.bool(forKey: "isMonitoringEnabled")

        if let savedBlockList = UserDefaults.standard.array(forKey: "distractingAppsBlockList") as? [String] {
            distractingAppsBlockList = Set(savedBlockList)
        }

        // Reset daily stats at midnight
        checkAndResetDailyStats()
    }

    // MARK: - Emergency Pause
    func togglePause() {
        isPaused.toggle()
    }

    func pauseFor(minutes: Int) {
        isPaused = true
        // Schedule auto-resume
        DispatchQueue.main.asyncAfter(deadline: .now() + .seconds(minutes * 60)) { [weak self] in
            self?.isPaused = false
        }
    }

    // MARK: - Distraction Session
    func startDistractionSession() {
        currentlyInDistractingApp = true
        distractingAppSessionStart = Date()
    }

    func endDistractionSession() {
        currentlyInDistractingApp = false
        if let start = distractingAppSessionStart {
            let duration = Date().timeIntervalSince(start)
            todayDistractionMinutes += Int(duration / 60)
            UserDefaults.standard.set(todayDistractionMinutes, forKey: "todayDistractionMinutes")
        }
        distractingAppSessionStart = nil
    }

    func recordIgnoredPrompt() {
        ignoredPromptsCount += 1
        if ignoredPromptsCount >= 3 {
            escalateIntensity()
        }
    }

    func recordRespondedPrompt() {
        ignoredPromptsCount = 0
        // Gradually de-escalate if responding consistently
        if escalationLevel > 0 {
            escalationLevel -= 1
        }
    }

    func escalateIntensity() {
        escalationLevel = min(escalationLevel + 1, 5)
    }

    // MARK: - Check-in Timing
    func updateCheckInInterval() {
        // Base interval: 3 minutes
        // Level 0: 3 minutes
        // Level 1: 2 minutes
        // Level 2: 90 seconds
        // Level 3: 60 seconds
        // Level 4+: 30 seconds

        switch escalationLevel {
        case 0:
            checkInIntervalSeconds = 180
        case 1:
            checkInIntervalSeconds = 120
        case 2:
            checkInIntervalSeconds = 90
        case 3:
            checkInIntervalSeconds = 60
        default:
            checkInIntervalSeconds = 30
        }
    }

    func scheduleNextCheckIn() {
        nextCheckInTime = Date().addingTimeInterval(checkInIntervalSeconds)
    }

    // MARK: - Daily Reset
    func checkAndResetDailyStats() {
        let lastReset = UserDefaults.standard.object(forKey: "lastStatsReset") as? Date ?? Date.distantPast
        let calendar = Calendar.current

        if !calendar.isDateInToday(lastReset) {
            // Reset daily counters
            todayDistractionMinutes = 0
            ignoredPromptsCount = 0
            escalationLevel = 0
            UserDefaults.standard.set(Date(), forKey: "lastStatsReset")
            UserDefaults.standard.set(0, forKey: "todayDistractionMinutes")
        } else {
            // Load today's stats
            todayDistractionMinutes = UserDefaults.standard.integer(forKey: "todayDistractionMinutes")
        }
    }
}
