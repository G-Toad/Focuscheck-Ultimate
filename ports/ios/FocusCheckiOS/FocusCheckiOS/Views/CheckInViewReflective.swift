//
//  CheckInViewReflective.swift
//  FocusCheckiOS
//
//  Full-screen check-in with FORCED TEXT REFLECTION
//  No buttons - must type out thoughts and confront reality
//

import SwiftUI

struct CheckInViewReflective: View {
    @Environment(\.dismiss) var dismiss
    @EnvironmentObject var appState: AppState

    @State private var currentStage: Stage = .initial
    @State private var responseText: String = ""
    @State private var errorMessage: String?
    @State private var timeElapsed: TimeInterval = 0
    @State private var timer: Timer?
    @State private var challenge: Challenge?
    @State private var showingKeyboard = false

    let startTime = Date()
    let spamDetector = SpamDetector()
    let challengeSystem = ChallengeSystem()

    enum Stage {
        case initial            // "Are you focused or distracted?"
        case focusedReflection  // "What are you working on?"
        case distractedReflection // "What are you wasting time on?"
    }

    var intensityLevel: Int {
        switch timeElapsed {
        case 0..<10: return 0
        case 10..<20: return 1
        case 20..<30: return 2
        default: return 3
        }
    }

    var backgroundColor: Color {
        switch intensityLevel {
        case 0: return Color(red: 0.05, green: 0.05, blue: 0.1)
        case 1: return Color(red: 0.1, green: 0.05, blue: 0.05)
        case 2: return Color(red: 0.15, green: 0.0, blue: 0.0)
        default: return Color.red.opacity(0.3)
        }
    }

    var body: some View {
        ZStack {
            backgroundColor
                .ignoresSafeArea()
                .animation(.easeInOut(duration: 0.5), value: intensityLevel)

            VStack(spacing: 0) {
                // Header
                VStack(spacing: 12) {
                    Text(headerText)
                        .font(.system(size: 28, weight: .bold))
                        .foregroundColor(.white)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)

                    if let challenge = challenge {
                        Text(challenge.question)
                            .font(.title3)
                            .foregroundColor(.orange)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal)
                            .padding(.top, 8)

                        if !challenge.hint.isEmpty && timeElapsed > 10 {
                            Text("Hint: \(challenge.hint)")
                                .font(.caption)
                                .foregroundColor(.gray)
                                .italic()
                                .multilineTextAlignment(.center)
                                .padding(.horizontal)
                                .padding(.top, 4)
                        }
                    } else {
                        Text(subtitleText)
                            .font(.title3)
                            .foregroundColor(.white.opacity(0.7))
                            .multilineTextAlignment(.center)
                            .padding(.horizontal)
                    }

                    // Timer
                    Text(String(format: "%.0fs", timeElapsed))
                        .font(.system(size: 20, weight: .medium, design: .monospaced))
                        .foregroundColor(intensityLevel >= 2 ? .red : .gray)
                }
                .padding(.top, 40)

                Spacer()

                // Main Content
                switch currentStage {
                case .initial:
                    initialChoiceView
                case .focusedReflection, .distractedReflection:
                    reflectionInputView
                }

                Spacer()

                // Error message
                if let error = errorMessage {
                    Text(error)
                        .font(.subheadline)
                        .foregroundColor(.red)
                        .multilineTextAlignment(.center)
                        .padding()
                        .background(Color.black.opacity(0.5))
                        .cornerRadius(8)
                        .padding(.horizontal)
                        .padding(.bottom, 8)
                }

                // Keyboard spacer
                if showingKeyboard {
                    Color.clear.frame(height: 300)
                }
            }
        }
        .onAppear {
            startTimer()
        }
        .onDisappear {
            timer?.invalidate()
        }
    }

    // MARK: - Initial Choice View
    var initialChoiceView: some View {
        VStack(spacing: 20) {
            Button(action: {
                handleInitialChoice(focused: true)
            }) {
                Text("I'm Being Productive")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 20)
                    .background(Color.green.opacity(0.3))
                    .cornerRadius(16)
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(Color.green, lineWidth: 2)
                    )
            }

            Button(action: {
                handleInitialChoice(focused: false)
            }) {
                Text("I'm Distracted")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 20)
                    .background(Color.red.opacity(0.3))
                    .cornerRadius(16)
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(Color.red, lineWidth: 2)
                    )
            }
        }
        .padding(.horizontal, 32)
    }

    // MARK: - Reflection Input View
    var reflectionInputView: some View {
        VStack(spacing: 16) {
            // Text input with dark styling
            TextEditor(text: $responseText)
                .font(.system(size: 18))
                .foregroundColor(.white)
                .scrollContentBackground(.hidden)
                .background(Color.black.opacity(0.3))
                .cornerRadius(12)
                .frame(height: 150)
                .padding(.horizontal, 24)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(challenge != nil ? Color.orange : Color.blue, lineWidth: 2)
                        .padding(.horizontal, 24)
                )
                .onTapGesture {
                    showingKeyboard = true
                }

            // Character count
            Text("\(responseText.count) characters")
                .font(.caption)
                .foregroundColor(.gray)

            // Submit button
            Button(action: validateAndSubmit) {
                Text("Submit")
                    .font(.headline)
                    .fontWeight(.bold)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                    .background(responseText.isEmpty ? Color.gray : Color.blue)
                    .cornerRadius(12)
            }
            .disabled(responseText.isEmpty)
            .padding(.horizontal, 24)

            // Skip button (only for non-challenge or early in timer)
            if challenge == nil || timeElapsed < 30 {
                Button(action: {
                    // Go back to initial choice
                    currentStage = .initial
                    responseText = ""
                    errorMessage = nil
                }) {
                    Text("Go Back")
                        .font(.subheadline)
                        .foregroundColor(.gray)
                }
            }
        }
    }

    // MARK: - Computed Properties
    var headerText: String {
        switch currentStage {
        case .initial:
            return "Check-In Time"
        case .focusedReflection:
            return challenge != nil ? "Before you continue..." : "Tell me what you're working on"
        case .distractedReflection:
            return challenge != nil ? "Let's be honest..." : "What are you doing right now?"
        }
    }

    var subtitleText: String {
        switch currentStage {
        case .initial:
            return "Be honest with yourself."
        case .focusedReflection:
            return "Type out what you're working on and why it matters."
        case .distractedReflection:
            return "Type out what you're wasting time on and the consequences."
        }
    }

    // MARK: - Actions
    private func handleInitialChoice(focused: Bool) {
        if focused {
            // Select challenge for studying context
            challenge = challengeSystem.getChallenge(context: "studying")
            currentStage = .focusedReflection
        } else {
            // Select challenge for wasting context (more aggressive)
            challenge = challengeSystem.getChallenge(context: "wasting")
            currentStage = .distractedReflection
        }
        responseText = ""
        errorMessage = nil
        showingKeyboard = true
    }

    private func validateAndSubmit() {
        errorMessage = nil

        // Step 1: Spam detection
        let (isValidSpam, spamError) = spamDetector.isValid(responseText, timeElapsed: timeElapsed)
        if !isValidSpam {
            errorMessage = spamError
            return
        }

        // Step 2: Challenge validation (if challenge active)
        if let challenge = challenge {
            let (isValidChallenge, challengeError) = challengeSystem.validateResponse(responseText, challenge: challenge)
            if !isValidChallenge {
                errorMessage = challengeError
                return
            }
        }

        // Success - log and dismiss
        logResponse()
        appState.recordRespondedPrompt()
        dismiss()
    }

    private func logResponse() {
        let logEntry: [String: Any] = [
            "timestamp": Date(),
            "stage": String(describing: currentStage),
            "response": responseText,
            "latency_seconds": timeElapsed,
            "had_challenge": challenge != nil,
            "challenge_id": challenge?.id ?? "",
            "escalation_level": appState.escalationLevel,
            "distraction_minutes_today": appState.todayDistractionMinutes
        ]

        // Save to UserDefaults
        var logs = UserDefaults.standard.array(forKey: "checkInLogs") as? [[String: Any]] ?? []
        logs.append(logEntry)
        UserDefaults.standard.set(logs, forKey: "checkInLogs")

        print("📊 Check-in logged: \(currentStage) - '\(responseText.prefix(50))'")
    }

    private func startTimer() {
        timer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { _ in
            timeElapsed = Date().timeIntervalSince(startTime)

            // Escalate app state if taking too long
            if timeElapsed > 30 && appState.escalationLevel < 3 {
                appState.escalateIntensity()
            }
        }
    }
}

struct CheckInViewReflective_Previews: PreviewProvider {
    static var previews: some View {
        CheckInViewReflective()
            .environmentObject(AppState())
    }
}
