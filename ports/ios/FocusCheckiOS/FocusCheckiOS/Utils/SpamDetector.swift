//
//  SpamDetector.swift
//  FocusCheckiOS
//
//  Multi-layered spam detection to prevent mindless/gibberish responses
//

import Foundation

struct SpamDetector {
    struct Config {
        // Gibberish detection
        var minVowelRatio: Double = 0.15
        var maxVowelRatio: Double = 0.75
        var minUniqueCharRatio: Double = 0.3

        // Repetition
        var maxConsecutiveChars: Int = 3
        var maxPatternRepetition: Int = 4

        // Spacing
        var minLengthRequireSpaces: Int = 20

        // Keyboard patterns
        var minKeyboardSequenceLength: Int = 5

        // Dictionary
        var minRealWordRatio: Double = 0.5
        var minWordLength: Int = 2

        // Timing
        var minTimeToSubmit: Double = 2.0
        var flagIfUnder: Double = 1.0

        // Banned/vague words
        var bannedWords: [String] = ["idk", "dunno", "meh", "whatever"]
        var vagueWords: [String] = ["stuff", "things", "something", "nothing"]
    }

    let config: Config
    private let dictionary: Set<String>

    init(config: Config = Config()) {
        self.config = config
        self.dictionary = Self.loadDictionary()
    }

    // MARK: - Main Validation
    func isValid(_ text: String, timeElapsed: TimeInterval? = nil) -> (Bool, String?) {
        let text = text.trimmingCharacters(in: .whitespacesAndNewlines)

        if text.isEmpty {
            return (false, "Please provide an answer")
        }

        var reasons: [String] = []

        // Check 1: Gibberish
        if let reason = checkGibberish(text) {
            reasons.append(reason)
        }

        // Check 2: Repetition
        if let reason = checkRepetition(text) {
            reasons.append(reason)
        }

        // Check 3: Spacing
        if let reason = checkSpacing(text) {
            reasons.append(reason)
        }

        // Check 4: Keyboard patterns
        if let reason = checkKeyboardPatterns(text) {
            reasons.append(reason)
        }

        // Check 5: Dictionary
        if let reason = checkDictionary(text) {
            reasons.append(reason)
        }

        // Check 6: Timing
        if let time = timeElapsed, let reason = checkTiming(time, text: text) {
            reasons.append(reason)
        }

        // Check 7: Vague words
        if let reason = checkVagueWords(text) {
            reasons.append(reason)
        }

        if reasons.isEmpty {
            return (true, nil)
        } else {
            let message = "Invalid response:\n\n• " + reasons.joined(separator: "\n• ") +
                         "\n\nPlease provide a thoughtful, honest answer."
            return (false, message)
        }
    }

    // MARK: - Detection Methods
    private func checkGibberish(_ text: String) -> String? {
        let letters = text.lowercased().filter { $0.isLetter }
        guard !letters.isEmpty else { return "No actual letters detected" }

        // Vowel ratio
        let vowels = letters.filter { "aeiou".contains($0) }
        let vowelRatio = Double(vowels.count) / Double(letters.count)

        if vowelRatio < config.minVowelRatio {
            return "Too few vowels (unusual pattern)"
        }
        if vowelRatio > config.maxVowelRatio {
            return "Too many vowels (unusual pattern)"
        }

        // Character diversity
        let uniqueRatio = Double(Set(letters).count) / Double(letters.count)
        if uniqueRatio < config.minUniqueCharRatio {
            return "Too many repeated characters (low diversity)"
        }

        return nil
    }

    private func checkRepetition(_ text: String) -> String? {
        let maxConsec = config.maxConsecutiveChars

        // Check consecutive identical characters
        for i in 0..<(text.count - maxConsec) {
            let start = text.index(text.startIndex, offsetBy: i)
            let chars = text[start...].prefix(maxConsec + 1)
            let charsArray = Array(chars)

            if charsArray.allSatisfy({ $0 == charsArray[0] }) {
                return "Repeated character detected: '\(String(repeating: String(charsArray[0]), count: maxConsec + 1))'"
            }
        }

        // Check pattern repetition
        let textClean = text.lowercased().replacingOccurrences(of: " ", with: "")
        for patternLen in 2...5 {
            for i in 0..<(textClean.count - patternLen * 2) {
                let start = textClean.index(textClean.startIndex, offsetBy: i)
                let pattern = String(textClean[start..<textClean.index(start, offsetBy: patternLen)])

                var count = 0
                var pos = i
                while pos < textClean.count - patternLen {
                    let checkStart = textClean.index(textClean.startIndex, offsetBy: pos)
                    let checkEnd = textClean.index(checkStart, offsetBy: patternLen)
                    let checkPattern = String(textClean[checkStart..<checkEnd])

                    if checkPattern == pattern {
                        count += 1
                        pos += patternLen
                    } else {
                        break
                    }
                }

                if count > config.maxPatternRepetition {
                    return "Repeated pattern detected: '\(pattern)' x \(count)"
                }
            }
        }

        return nil
    }

    private func checkSpacing(_ text: String) -> String? {
        if text.count > config.minLengthRequireSpaces && !text.contains(" ") {
            return "No spaces in \(text.count)-character text (keyboard mashing?)"
        }
        return nil
    }

    private func checkKeyboardPatterns(_ text: String) -> String? {
        let textLower = text.lowercased()
        let minSeq = config.minKeyboardSequenceLength

        let keyboardRows = [
            "qwertyuiop",
            "asdfghjkl",
            "zxcvbnm",
            "1234567890"
        ]

        for row in keyboardRows {
            // Forward sequences
            for i in 0...(row.count - minSeq) {
                let start = row.index(row.startIndex, offsetBy: i)
                let end = row.index(start, offsetBy: minSeq)
                let sequence = String(row[start..<end])

                if textLower.contains(sequence) {
                    return "Keyboard pattern detected: '\(sequence)'"
                }
            }

            // Reverse sequences
            let reversed = String(row.reversed())
            for i in 0...(reversed.count - minSeq) {
                let start = reversed.index(reversed.startIndex, offsetBy: i)
                let end = reversed.index(start, offsetBy: minSeq)
                let sequence = String(reversed[start..<end])

                if textLower.contains(sequence) {
                    return "Keyboard pattern detected: '\(sequence)' (reversed)"
                }
            }
        }

        return nil
    }

    private func checkDictionary(_ text: String) -> String? {
        let words = text.lowercased()
            .components(separatedBy: .whitespacesAndNewlines)
            .map { $0.trimmingCharacters(in: .punctuationCharacters) }
            .filter { $0.count >= config.minWordLength }

        guard !words.isEmpty else {
            return "No recognizable words"
        }

        let realWords = words.filter { dictionary.contains($0) }
        let ratio = Double(realWords.count) / Double(words.count)

        if ratio < config.minRealWordRatio {
            return "Too few real words (\(Int(ratio * 100))% recognized)"
        }

        return nil
    }

    private func checkTiming(_ timeElapsed: TimeInterval, text: String) -> String? {
        if timeElapsed < config.flagIfUnder {
            return String(format: "Answered in %.1fs (suspiciously fast)", timeElapsed)
        }

        // Typing speed check
        if timeElapsed > 0 {
            let charsPerSecond = Double(text.count) / timeElapsed
            if charsPerSecond > 15 {
                return String(format: "Typing speed too fast (%.1f chars/sec)", charsPerSecond)
            }
        }

        return nil
    }

    private func checkVagueWords(_ text: String) -> String? {
        let textLower = text.lowercased()

        // Check banned words
        for word in config.bannedWords {
            if textLower.contains(word) {
                return "Dismissive word detected: '\(word)'"
            }
        }

        // Check if ONLY vague words (short responses)
        let words = textLower.components(separatedBy: .whitespacesAndNewlines)
        if words.count <= 3 {
            let vagueCount = words.filter { config.vagueWords.contains($0) }.count
            if vagueCount == words.count {
                return "Answer too vague (only generic words)"
            }
        }

        return nil
    }

    // MARK: - Dictionary Loading
    private static func loadDictionary() -> Set<String> {
        return Set([
            // Common words
            "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
            "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
            "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
            "or", "an", "will", "my", "one", "all", "would", "there", "their", "what",
            "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
            "when", "make", "can", "like", "time", "no", "just", "him", "know", "take",

            // Study/work related
            "study", "studying", "learn", "learning", "read", "reading", "write", "writing",
            "homework", "assignment", "exam", "test", "quiz", "practice", "work", "working",
            "focus", "focused", "focusing", "thinking", "understand", "understanding",
            "chapter", "book", "page", "problem", "question", "answer", "solve", "solving",
            "math", "science", "history", "english", "biology", "chemistry", "physics",

            // Programming
            "python", "java", "javascript", "code", "coding", "program", "programming",
            "computer", "software", "data", "algorithm", "function", "class", "method",
            "debug", "debugging", "compile", "run", "execute", "build", "test", "testing",

            // Procrastination
            "youtube", "twitter", "reddit", "instagram", "facebook", "tiktok", "social",
            "media", "video", "videos", "game", "games", "gaming", "phone", "scroll",
            "scrolling", "browse", "browsing", "watch", "watching", "waste", "wasting",
            "procrastinate", "procrastinating", "distracted", "distraction", "avoid",
            "avoiding", "delay", "delaying", "postpone", "postponing",

            // Emotions
            "tired", "anxious", "anxiety", "stressed", "stress", "worried", "worry",
            "scared", "afraid", "fear", "guilt", "guilty", "frustrated", "frustration",
            "overwhelmed", "bored", "boring", "lazy", "unmotivated", "motivated",

            // Actions/commitment
            "need", "should", "must", "have", "doing", "done", "finish", "finished",
            "start", "started", "continue", "continuing", "stop", "stopped", "try",
            "trying", "attempt", "attempting", "complete", "completed", "goal", "achieve",
            "accomplish", "because", "tomorrow", "regret", "lying", "pretending", "hour",
            "hours", "instead",

            // Contractions
            "im", "id", "ill", "ive", "dont", "cant", "wont", "isnt", "arent",
            "wasnt", "werent", "hasnt", "havent", "didnt", "doesnt"
        ])
    }
}
