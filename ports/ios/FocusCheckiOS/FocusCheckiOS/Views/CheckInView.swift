//
//  CheckInView.swift
//  FocusCheckiOS
//
//  Full-screen check-in dialog with escalation effects
//

import SwiftUI
import AVFoundation

struct CheckInView: View {
    @Environment(\.dismiss) var dismiss
    @EnvironmentObject var appState: AppState

    @State private var timeElapsed: TimeInterval = 0
    @State private var timer: Timer?
    @State private var shakeOffset: CGFloat = 0
    @State private var pulseScale: CGFloat = 1.0
    @State private var showingIntensity = false
    @State private var audioPlayer: AVAudioPlayer?

    let startTime = Date()

    var intensityLevel: Int {
        switch timeElapsed {
        case 0..<10: return 0
        case 10..<20: return 1
        case 20..<30: return 2
        case 30..<45: return 3
        default: return 4
        }
    }

    var backgroundColor: Color {
        switch intensityLevel {
        case 0: return Color(red: 0.05, green: 0.05, blue: 0.1)
        case 1: return Color(red: 0.1, green: 0.05, blue: 0.05)
        case 2: return Color(red: 0.15, green: 0.0, blue: 0.0)
        case 3: return Color.red.opacity(0.3)
        default: return Color.red.opacity(0.5)
        }
    }

    var body: some View {
        ZStack {
            // Animated background
            backgroundColor
                .ignoresSafeArea()
                .animation(.easeInOut(duration: 0.5), value: intensityLevel)

            VStack(spacing: 40) {
                // Header
                VStack(spacing: 12) {
                    if intensityLevel >= 3 {
                        Text("🚨 WAKE UP 🚨")
                            .font(.system(size: 36, weight: .black))
                            .foregroundColor(.red)
                            .scaleEffect(pulseScale)
                    } else {
                        Text("Check-In Time")
                            .font(.system(size: 32, weight: .bold))
                            .foregroundColor(.white)
                    }

                    Text("Are you being productive right now?")
                        .font(.title3)
                        .foregroundColor(.white.opacity(0.8))
                        .multilineTextAlignment(.center)

                    // Timer
                    Text(String(format: "%.0fs", timeElapsed))
                        .font(.system(size: 24, weight: .medium, design: .monospaced))
                        .foregroundColor(intensityLevel >= 2 ? .red : .gray)
                }

                // Stats reminder (if distracted)
                if appState.todayDistractionMinutes > 0 {
                    VStack(spacing: 8) {
                        Text("Time wasted today:")
                            .font(.subheadline)
                            .foregroundColor(.white.opacity(0.6))

                        Text("\(appState.todayDistractionMinutes) minutes")
                            .font(.system(size: 28, weight: .bold))
                            .foregroundColor(.orange)
                    }
                    .padding()
                    .background(Color.black.opacity(0.3))
                    .cornerRadius(12)
                }

                Spacer()

                // Action Buttons
                VStack(spacing: 20) {
                    Button(action: {
                        respondFocused()
                    }) {
                        Text("✅ Yes, I'm Focused")
                            .font(.title2)
                            .fontWeight(.bold)
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 20)
                            .background(Color.green)
                            .cornerRadius(16)
                    }
                    .offset(x: intensityLevel >= 2 ? shakeOffset : 0)

                    Button(action: {
                        respondDistracted()
                    }) {
                        Text("⚠️ No, Got Distracted")
                            .font(.title2)
                            .fontWeight(.bold)
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 20)
                            .background(Color.red)
                            .cornerRadius(16)
                    }
                    .offset(x: intensityLevel >= 2 ? -shakeOffset : 0)
                }
                .padding(.horizontal, 24)

                if intensityLevel < 3 {
                    Button(action: {
                        // Snooze option (only available early)
                        snooze()
                    }) {
                        Text("Snooze 5 min")
                            .font(.subheadline)
                            .foregroundColor(.gray)
                    }
                }

                Spacer()
            }
            .padding()
        }
        .onAppear {
            startTimer()
            startEffects()
        }
        .onDisappear {
            timer?.invalidate()
            audioPlayer?.stop()
        }
    }

    // MARK: - Actions
    private func respondFocused() {
        appState.recordRespondedPrompt()
        logResponse("Focused", latency: timeElapsed)
        dismiss()
    }

    private func respondDistracted() {
        appState.recordRespondedPrompt()
        appState.todayDistractionMinutes += 1 // Acknowledge distraction
        logResponse("Distracted", latency: timeElapsed)
        dismiss()
    }

    private func snooze() {
        appState.pauseFor(minutes: 5)
        dismiss()
    }

    // MARK: - Timer & Effects
    private func startTimer() {
        timer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { _ in
            timeElapsed = Date().timeIntervalSince(startTime)

            // Escalate app state if taking too long
            if timeElapsed > 30 && appState.escalationLevel < 3 {
                appState.escalateIntensity()
            }
        }
    }

    private func startEffects() {
        // Pulse animation for high intensity
        withAnimation(Animation.easeInOut(duration: 0.5).repeatForever(autoreverses: true)) {
            pulseScale = 1.1
        }

        // Shake animation for level 2+
        Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { timer in
            if intensityLevel >= 2 {
                withAnimation(.linear(duration: 0.1)) {
                    shakeOffset = CGFloat.random(in: -5...5)
                }
            } else {
                timer.invalidate()
            }
        }

        // Play alarm sound at level 3+
        if intensityLevel >= 3 {
            playAlarmSound()
        }
    }

    private func playAlarmSound() {
        // Play a repeating alarm tone
        guard let url = Bundle.main.url(forResource: "alarm", withExtension: "mp3") else {
            // Fallback: use system sound
            AudioServicesPlaySystemSound(1005) // Long beep
            return
        }

        do {
            audioPlayer = try AVAudioPlayer(contentsOf: url)
            audioPlayer?.numberOfLoops = -1 // Infinite loop
            audioPlayer?.volume = 0.8
            audioPlayer?.play()
        } catch {
            print("Failed to play alarm: \(error)")
        }
    }

    private func logResponse(_ response: String, latency: TimeInterval) {
        print("📊 Check-in response: \(response) after \(String(format: "%.1f", latency))s")

        // Log to analytics or database here
        let logEntry: [String: Any] = [
            "timestamp": Date(),
            "response": response,
            "latency_seconds": latency,
            "intensity_level": intensityLevel,
            "escalation_level": appState.escalationLevel,
            "distraction_minutes_today": appState.todayDistractionMinutes
        ]

        // Save to UserDefaults or CloudKit
        var logs = UserDefaults.standard.array(forKey: "checkInLogs") as? [[String: Any]] ?? []
        logs.append(logEntry)
        UserDefaults.standard.set(logs, forKey: "checkInLogs")
    }
}

struct CheckInView_Previews: PreviewProvider {
    static var previews: some View {
        CheckInView()
            .environmentObject(AppState())
    }
}
