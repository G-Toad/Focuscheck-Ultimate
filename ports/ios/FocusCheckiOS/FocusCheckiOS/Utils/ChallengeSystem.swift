//
//  ChallengeSystem.swift
//  FocusCheckiOS
//
//  Challenge system that requires specific keywords in responses
//  Forces genuine reflection by creating cognitive barriers
//

import Foundation

struct Challenge {
    let id: String
    let question: String
    let requiredWords: [String]
    let requiredMode: RequiredMode  // "any" or "all"
    let bannedPhrases: [String]
    let errorMissing: String
    let errorVague: String?
    let hint: String

    enum RequiredMode {
        case any  // Need at least one required word
        case all  // Need all required words
    }
}

struct ChallengeSystem {
    struct Config {
        var studyingFrequency: Double = 0.5  // 50% chance
        var wastingFrequency: Double = 0.7   // 70% chance (more aggressive)
        var minWords: Int = 3
        var minTotalLength: Int = 10
    }

    let config: Config

    // MARK: - Challenge Pools
    private let studyingChallenges: [Challenge] = [
        Challenge(
            id: "learning_specificity",
            question: "What EXACTLY are you learning right now?\n(Must include 'learning' or 'studying')",
            requiredWords: ["learning", "studying", "understand", "reading"],
            requiredMode: .any,
            bannedPhrases: [],
            errorMissing: "You must include 'learning' or 'studying' and be specific about the topic.",
            errorVague: "Too vague. Name the specific topic, chapter, or concept.",
            hint: "Example: 'I'm learning how to solve quadratic equations'"
        ),
        Challenge(
            id: "goal_connection",
            question: "What GOAL does this serve?\n(Must include 'goal' or 'achieve')",
            requiredWords: ["goal", "achieve", "accomplish", "complete", "pass"],
            requiredMode: .any,
            bannedPhrases: [],
            errorMissing: "You must include 'goal', 'achieve', or similar and state your purpose.",
            errorVague: "Be specific about what you're trying to achieve.",
            hint: "Example: 'My goal is to pass Friday's chemistry exam'"
        ),
        Challenge(
            id: "will_commitment",
            question: "What WILL you accomplish in the next 20 minutes?\n(Must include 'will' + specific action)",
            requiredWords: ["will"],
            requiredMode: .all,
            bannedPhrases: ["try", "maybe", "might"],
            errorMissing: "You must include 'will' and state a concrete action.",
            errorVague: "Don't say 'try' or 'maybe' - commit to a specific action.",
            hint: "Example: 'I will finish reading chapter 3'"
        ),
        Challenge(
            id: "output_expectation",
            question: "What specific OUTPUT will you have after this?\n(Must include 'finished' or 'completed' or 'done')",
            requiredWords: ["finished", "completed", "done", "wrote", "solved"],
            requiredMode: .any,
            bannedPhrases: [],
            errorMissing: "You must describe what you'll have finished/completed/done.",
            errorVague: "Be specific - how many problems? Which chapter?",
            hint: "Example: 'I'll have completed 10 practice problems'"
        )
    ]

    private let wastingChallenges: [Challenge] = [
        Challenge(
            id: "wasting_acknowledgment",
            question: "What are the consequences of your current actions?\n(Must include 'wasting')",
            requiredWords: ["wasting", "waste"],
            requiredMode: .any,
            bannedPhrases: ["wasting time"],  // Too generic
            errorMissing: "You must acknowledge what you're 'wasting' - be specific about the cost.",
            errorVague: "'Wasting time' is too vague. What are you wasting? Your chance? Your evening?",
            hint: "Example: 'I'm wasting my last chance to prepare before tomorrow's test'"
        ),
        Challenge(
            id: "should_gap",
            question: "What are you doing instead of what you SHOULD do?\n(Must include 'should')",
            requiredWords: ["should"],
            requiredMode: .all,
            bannedPhrases: [],
            errorMissing: "You must include 'should' and contrast what you're doing vs what you should do.",
            errorVague: "Show the contrast: 'doing X instead of Y that I should do'.",
            hint: "Example: 'Scrolling Reddit instead of the essay I should be writing'"
        ),
        Challenge(
            id: "because_reasoning",
            question: "Why are you avoiding what matters right now?\n(Must include 'because')",
            requiredWords: ["because"],
            requiredMode: .all,
            bannedPhrases: ["because reasons", "just because"],
            errorMissing: "You must include 'because' and explain the real reason you're avoiding work.",
            errorVague: "Too shallow. Dig deeper - what's the REAL reason?",
            hint: "Example: 'Because starting the assignment feels overwhelming and scary'"
        ),
        Challenge(
            id: "hour_projection",
            question: "What will happen if you continue THIS for ONE MORE HOUR?\n(Must include 'hour' or 'hours')",
            requiredWords: ["hour", "hours"],
            requiredMode: .any,
            bannedPhrases: [],
            errorMissing: "You must include 'hour' or 'hours' and describe the consequence.",
            errorVague: "Be concrete - what EXACTLY will happen in an hour?",
            hint: "Example: 'In another hour I'll have zero time left and will panic'"
        ),
        Challenge(
            id: "tomorrow_regret",
            question: "What will TOMORROW you regret about RIGHT NOW you?\n(Must include 'tomorrow' or 'regret')",
            requiredWords: ["tomorrow", "regret"],
            requiredMode: .any,
            bannedPhrases: ["no regrets", "wont regret", "nothing"],
            errorMissing: "You must include 'tomorrow' or 'regret' and acknowledge future consequences.",
            errorVague: "Be honest - there WILL be regret. What will it be?",
            hint: "Example: 'Tomorrow I'll regret not using these 2 free hours to study'"
        ),
        Challenge(
            id: "fear_acknowledgment",
            question: "What are you ACTUALLY afraid of right now?\n(Must include 'scared', 'afraid', or 'anxious')",
            requiredWords: ["scared", "afraid", "anxious", "fear", "worried"],
            requiredMode: .any,
            bannedPhrases: ["not scared", "not afraid", "not anxious"],
            errorMissing: "You must acknowledge the fear/anxiety. Use 'scared', 'afraid', or 'anxious'.",
            errorVague: "If you're avoiding work, there's fear underneath. What is it?",
            hint: "Example: 'I'm afraid I'll fail even if I study hard'"
        ),
        Challenge(
            id: "lying_confrontation",
            question: "How are you lying to yourself right now?\n(Must include 'lying', 'pretending', or 'telling myself')",
            requiredWords: ["lying", "pretending", "telling myself", "lie", "pretend"],
            requiredMode: .any,
            bannedPhrases: ["not lying", "not pretending"],
            errorMissing: "You must acknowledge the self-deception. Use 'lying', 'pretending', or 'telling myself'.",
            errorVague: "Procrastination always involves self-deception. What's the lie?",
            hint: "Example: 'I'm lying to myself that I'll do it later tonight'"
        )
    ]

    // MARK: - Challenge Selection
    func shouldShowChallenge(context: String) -> Bool {
        let frequency = context == "studying" ? config.studyingFrequency : config.wastingFrequency
        return Double.random(in: 0...1) < frequency
    }

    func getChallenge(context: String) -> Challenge? {
        guard shouldShowChallenge(context: context) else {
            return nil
        }

        let pool = context == "studying" ? studyingChallenges : wastingChallenges
        return pool.randomElement()
    }

    // MARK: - Validation
    func validateResponse(_ response: String, challenge: Challenge) -> (Bool, String?) {
        let response = response.trimmingCharacters(in: .whitespacesAndNewlines)
        let responseLower = response.lowercased()

        // Check minimum length
        if response.count < config.minTotalLength {
            return (false, "Response too short. Need at least \(config.minTotalLength) characters.")
        }

        // Check minimum word count
        let words = response.components(separatedBy: .whitespacesAndNewlines).filter { $0.count > 1 }
        if words.count < config.minWords {
            return (false, "Response too short. Need at least \(config.minWords) words.")
        }

        // Check required words
        switch challenge.requiredMode {
        case .any:
            let hasRequiredWord = challenge.requiredWords.contains { responseLower.contains($0) }
            if !hasRequiredWord {
                return (false, challenge.errorMissing)
            }

        case .all:
            let missingWords = challenge.requiredWords.filter { !responseLower.contains($0) }
            if !missingWords.isEmpty {
                return (false, challenge.errorMissing)
            }
        }

        // Check banned phrases
        for phrase in challenge.bannedPhrases {
            if responseLower.contains(phrase) {
                return (false, challenge.errorVague ?? "That phrase is too generic. Be more specific.")
            }
        }

        // Check for denial patterns
        for requiredWord in challenge.requiredWords {
            let denialPatterns = ["not \(requiredWord)", "no \(requiredWord)", "don't \(requiredWord)"]
            for denial in denialPatterns {
                if responseLower.contains(denial) {
                    return (false, "Don't deny it. Acknowledge the truth using '\(requiredWord)'.")
                }
            }
        }

        // Check for generic "wasting time" if that's banned
        if challenge.id == "wasting_acknowledgment" && responseLower == "wasting time" {
            return (false, challenge.errorVague ?? "'Wasting time' is too generic.")
        }

        return (true, nil)
    }
}
