//
//  ContentView.swift
//  FocusCheckiOS
//
//  Main app interface with stats and emergency pause
//

import SwiftUI

struct ContentView: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var notificationManager: NotificationManager
    @EnvironmentObject var monitorManager: ActivityMonitorManager

    @State private var showingCheckIn = false

    var body: some View {
        NavigationView {
            ZStack {
                // Background gradient
                LinearGradient(
                    colors: [Color.black, Color(red: 0.1, green: 0.05, blue: 0.15)],
                    startPoint: .top,
                    endPoint: .bottom
                )
                .ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 24) {
                        // Emergency Pause Button
                        EmergencyPauseButton()
                            .environmentObject(appState)
                            .environmentObject(notificationManager)
                            .environmentObject(monitorManager)

                        // Status Card
                        StatusCard()
                            .environmentObject(appState)

                        // Today's Stats
                        StatsCard()
                            .environmentObject(appState)

                        // Settings
                        SettingsCard()
                            .environmentObject(appState)
                            .environmentObject(monitorManager)

                        Spacer(minLength: 40)
                    }
                    .padding()
                }
            }
            .navigationTitle("FocusCheck")
            .navigationBarTitleDisplayMode(.large)
            .onReceive(NotificationCenter.default.publisher(for: .userIgnoredPrompt)) { _ in
                appState.recordIgnoredPrompt()
            }
            .onReceive(NotificationCenter.default.publisher(for: .userRespondedFocused)) { _ in
                appState.recordRespondedPrompt()
            }
            .onReceive(NotificationCenter.default.publisher(for: .userRespondedDistracted)) { _ in
                appState.recordRespondedPrompt()
                showingCheckIn = true
            }
        }
        .sheet(isPresented: $showingCheckIn) {
            CheckInViewReflective()
                .environmentObject(appState)
        }
    }
}

// MARK: - Emergency Pause Button
struct EmergencyPauseButton: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var notificationManager: NotificationManager
    @EnvironmentObject var monitorManager: ActivityMonitorManager

    @State private var showingPauseOptions = false

    var body: some View {
        VStack(spacing: 12) {
            if appState.isPaused {
                // Currently Paused
                Button(action: {
                    appState.isPaused = false
                    if appState.isMonitoringEnabled {
                        monitorManager.startMonitoring()
                    }
                }) {
                    HStack {
                        Image(systemName: "play.fill")
                            .font(.title2)
                        VStack(alignment: .leading) {
                            Text("PAUSED")
                                .font(.headline)
                            if let pausedAt = appState.pausedAt {
                                Text("Since \(pausedAt, style: .time)")
                                    .font(.caption)
                                    .foregroundColor(.gray)
                            }
                        }
                        Spacer()
                        Text("Resume")
                            .font(.headline)
                    }
                    .padding()
                    .frame(maxWidth: .infinity)
                    .background(Color.green.opacity(0.2))
                    .foregroundColor(.green)
                    .cornerRadius(16)
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(Color.green, lineWidth: 2)
                    )
                }
            } else {
                // Active - Show Pause Button
                Button(action: {
                    showingPauseOptions = true
                }) {
                    HStack {
                        Image(systemName: "pause.circle.fill")
                            .font(.title)
                            .foregroundColor(.orange)
                        VStack(alignment: .leading) {
                            Text("EMERGENCY PAUSE")
                                .font(.headline)
                                .foregroundColor(.white)
                            Text("Tap for emergency/critical situations")
                                .font(.caption)
                                .foregroundColor(.gray)
                        }
                        Spacer()
                    }
                    .padding()
                    .frame(maxWidth: .infinity)
                    .background(Color.orange.opacity(0.15))
                    .cornerRadius(16)
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(Color.orange.opacity(0.5), lineWidth: 2)
                    )
                }
            }
        }
        .confirmationDialog("Pause Monitoring", isPresented: $showingPauseOptions) {
            Button("Pause 5 minutes") {
                pauseFor(minutes: 5)
            }
            Button("Pause 15 minutes") {
                pauseFor(minutes: 15)
            }
            Button("Pause 1 hour") {
                pauseFor(minutes: 60)
            }
            Button("Pause indefinitely") {
                appState.isPaused = true
                notificationManager.cancelAllNotifications()
                monitorManager.stopMonitoring()
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("How long do you need to pause?")
        }
    }

    private func pauseFor(minutes: Int) {
        appState.pauseFor(minutes: minutes)
        notificationManager.cancelAllNotifications()
        monitorManager.stopMonitoring()

        // Schedule auto-resume notification
        DispatchQueue.main.asyncAfter(deadline: .now() + .seconds(minutes * 60 - 30)) {
            let content = UNMutableNotificationContent()
            content.title = "Pause Ending Soon"
            content.body = "FocusCheck will resume in 30 seconds"
            content.sound = .default

            let trigger = UNTimeIntervalNotificationTrigger(timeInterval: 1, repeats: false)
            let request = UNNotificationRequest(identifier: "pause-ending", content: content, trigger: trigger)
            UNUserNotificationCenter.current().add(request)
        }
    }
}

// MARK: - Status Card
struct StatusCard: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        VStack(spacing: 16) {
            HStack {
                VStack(alignment: .leading) {
                    Text("Status")
                        .font(.headline)
                        .foregroundColor(.gray)

                    HStack(spacing: 8) {
                        Circle()
                            .fill(appState.isPaused ? Color.orange : Color.green)
                            .frame(width: 12, height: 12)

                        Text(appState.isPaused ? "Paused" : "Monitoring")
                            .font(.title2)
                            .fontWeight(.bold)
                            .foregroundColor(.white)
                    }
                }

                Spacer()

                if appState.escalationLevel > 0 {
                    VStack {
                        Text("Level \(appState.escalationLevel)")
                            .font(.caption)
                            .foregroundColor(.red)
                        Image(systemName: "exclamationmark.triangle.fill")
                            .font(.title)
                            .foregroundColor(.red)
                    }
                }
            }

            if !appState.isPaused, let nextCheck = appState.nextCheckInTime {
                HStack {
                    Image(systemName: "clock.fill")
                        .foregroundColor(.blue)
                    Text("Next check-in: ")
                        .foregroundColor(.gray)
                    Text(nextCheck, style: .relative)
                        .foregroundColor(.white)
                }
                .font(.subheadline)
            }
        }
        .padding()
        .background(Color.white.opacity(0.05))
        .cornerRadius(16)
    }
}

// MARK: - Stats Card
struct StatsCard: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Today's Activity")
                .font(.headline)
                .foregroundColor(.gray)

            HStack(spacing: 20) {
                StatItem(
                    icon: "hourglass",
                    value: "\(appState.todayDistractionMinutes)",
                    unit: "min",
                    label: "Distracted",
                    color: .red
                )

                StatItem(
                    icon: "hand.raised.fill",
                    value: "\(appState.ignoredPromptsCount)",
                    unit: "",
                    label: "Ignored",
                    color: .orange
                )

                StatItem(
                    icon: "flame.fill",
                    value: "\(max(0, 3 - appState.ignoredPromptsCount))",
                    unit: "",
                    label: "Streak",
                    color: .green
                )
            }
        }
        .padding()
        .background(Color.white.opacity(0.05))
        .cornerRadius(16)
    }
}

struct StatItem: View {
    let icon: String
    let value: String
    let unit: String
    let label: String
    let color: Color

    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(color)

            HStack(alignment: .firstTextBaseline, spacing: 2) {
                Text(value)
                    .font(.title)
                    .fontWeight(.bold)
                    .foregroundColor(.white)
                if !unit.isEmpty {
                    Text(unit)
                        .font(.caption)
                        .foregroundColor(.gray)
                }
            }

            Text(label)
                .font(.caption)
                .foregroundColor(.gray)
        }
        .frame(maxWidth: .infinity)
    }
}

// MARK: - Settings Card
struct SettingsCard: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var monitorManager: ActivityMonitorManager

    var body: some View {
        VStack(spacing: 12) {
            Toggle(isOn: $appState.isMonitoringEnabled) {
                VStack(alignment: .leading) {
                    Text("YouTube Monitoring")
                        .font(.headline)
                    Text("Prompt me when using distracting apps")
                        .font(.caption)
                        .foregroundColor(.gray)
                }
            }
            .tint(.blue)
            .onChange(of: appState.isMonitoringEnabled) { newValue in
                if newValue && !appState.isPaused {
                    monitorManager.startMonitoring()
                } else {
                    monitorManager.stopMonitoring()
                }
            }

            Divider()

            HStack {
                Text("Check-in Interval")
                    .foregroundColor(.gray)
                Spacer()
                Text("\(Int(appState.checkInIntervalSeconds / 60)) min")
                    .foregroundColor(.white)
            }
            .font(.subheadline)
        }
        .padding()
        .background(Color.white.opacity(0.05))
        .cornerRadius(16)
    }
}
