"""
Challenge-based reflection system with hard constraints.

Implements barrier challenges that force genuine reflection by requiring
specific words or patterns in responses. Different challenges for studying
vs wasting time to maximize effectiveness.
"""

import random


class ChallengeSystem:
    """
    Manages challenge selection and validation.

    Challenges create cognitive barriers that prevent autopilot responses
    while simultaneously triggering self-reflection mechanisms.
    """

    def __init__(self, config=None):
        """
        Initialize challenge system.

        Args:
            config: Dictionary of challenge settings
        """
        self.config = config or self._default_config()
        self._init_challenges()

    def _default_config(self):
        """Default challenge configuration."""
        return {
            # Challenge frequency (0.0-1.0, probability of challenge appearing)
            "studying_challenge_frequency": 0.3,  # 30% of studying prompts
            "wasting_challenge_frequency": 0.5,   # 50% of wasting prompts

            # Minimum requirements
            "challenge_min_words": 3,             # Minimum word count (lowered from 5)
            "challenge_min_total_length": 10,     # Minimum character count (lowered from 20)

            # Challenge-specific settings
            "allow_challenge_skip": False,        # If True, can cancel challenge
        }

    def _init_challenges(self):
        """Initialize challenge pools."""

        # Challenges for STUDYING responses
        # Goal: Ensure they're actually studying and being specific
        self.studying_challenges = [
            {
                "id": "learning_specificity",
                "question": "What EXACTLY are you learning right now? (Must include 'learning' or 'studying')",
                "required_words": ["learning", "studying", "understand", "reading"],
                "required_word_mode": "any",  # Need at least one
                "banned_vague": ["stuff", "things", "homework", "work"],
                "error_missing": "You must include 'learning' or 'studying' and be specific about the topic.",
                "error_vague": "Too vague. Name the specific topic, chapter, or concept you're learning.",
            },
            {
                "id": "goal_connection",
                "question": "What GOAL does this study session serve? (Must include 'goal' or 'achieve')",
                "required_words": ["goal", "achieve", "accomplish", "complete", "pass"],
                "required_word_mode": "any",
                "error_missing": "You must include 'goal', 'achieve', 'accomplish', or similar and state your purpose.",
                "error_vague": "Be specific about what you're trying to achieve.",
            },
            {
                "id": "will_commitment",
                "question": "What WILL you accomplish in the next 20 minutes? (Must include 'will' + specific action)",
                "required_words": ["will"],
                "required_word_mode": "all",
                "must_contain_action": True,
                "banned_weak": ["try", "maybe", "might", "hopefully"],
                "error_missing": "You must include 'will' and state a concrete action you'll take.",
                "error_weak": "Don't say 'try' or 'maybe' - commit to a specific action.",
            },
            {
                "id": "output_expectation",
                "question": "What specific OUTPUT will you have after this? (Must include 'finished' or 'completed' or 'done')",
                "required_words": ["finished", "completed", "done", "wrote", "solved"],
                "required_word_mode": "any",
                "error_missing": "You must describe what you'll have finished/completed/done.",
                "error_vague": "Be specific - how many problems? Which chapter? What section?",
            },
        ]

        # Challenges for WASTING TIME responses
        # Goal: Force acknowledgment of waste and consequences
        self.wasting_challenges = [
            {
                "id": "wasting_acknowledgment",
                "question": "What are the consequences of your current actions? (Must include 'wasting')",
                "required_words": ["wasting", "waste"],
                "required_word_mode": "any",
                "banned_phrases": ["wasting time", "waste time", "wasting my time"],  # Too generic
                "error_missing": "You must acknowledge what you're 'wasting' - be specific about the cost.",
                "error_generic": "'Wasting time' is too vague. What are you wasting? Your chance? Your evening? Be specific.",
            },
            {
                "id": "should_gap",
                "question": "What are you doing instead of what you SHOULD do? (Must include 'should')",
                "required_words": ["should"],
                "required_word_mode": "all",
                "must_show_contrast": True,  # Must show "X instead of Y"
                "error_missing": "You must include 'should' and contrast what you're doing vs what you should do.",
                "error_no_contrast": "Show the contrast: 'doing X instead of Y that I should do'.",
            },
            {
                "id": "because_reasoning",
                "question": "Why are you avoiding what matters right now? (Must include 'because')",
                "required_words": ["because"],
                "required_word_mode": "all",
                "banned_phrases": ["because reasons", "just because"],
                "error_missing": "You must include 'because' and explain the real reason you're avoiding work.",
                "error_shallow": "Too shallow. Dig deeper - what's the REAL reason?",
            },
            {
                "id": "hour_projection",
                "question": "What will happen if you continue THIS for ONE MORE HOUR? (Must include 'hour' or 'hours')",
                "required_words": ["hour", "hours"],
                "required_word_mode": "any",
                "must_describe_consequence": True,
                "error_missing": "You must include 'hour' or 'hours' and describe the consequence.",
                "error_vague": "Be concrete - what EXACTLY will happen in an hour?",
            },
            {
                "id": "tomorrow_regret",
                "question": "What will TOMORROW you regret about RIGHT NOW you? (Must include 'tomorrow' or 'regret')",
                "required_words": ["tomorrow", "regret"],
                "required_word_mode": "any",
                "banned_phrases": ["no regrets", "won't regret", "nothing"],
                "error_missing": "You must include 'tomorrow' or 'regret' and acknowledge future consequences.",
                "error_denial": "Be honest - there WILL be regret. What will it be?",
            },
            {
                "id": "fear_acknowledgment",
                "question": "What are you ACTUALLY afraid of right now? (Must include 'scared', 'afraid', or 'anxious')",
                "required_words": ["scared", "afraid", "anxious", "fear", "worried"],
                "required_word_mode": "any",
                "banned_phrases": ["not scared", "not afraid", "not anxious"],
                "error_missing": "You must acknowledge the fear/anxiety. Use 'scared', 'afraid', or 'anxious'.",
                "error_denial": "If you're avoiding work, there's fear underneath. What is it?",
            },
            {
                "id": "lying_confrontation",
                "question": "How are you lying to yourself right now? (Must include 'lying', 'pretending', or 'telling myself')",
                "required_words": ["lying", "pretending", "telling myself", "lie", "pretend"],
                "required_word_mode": "any",
                "banned_phrases": ["not lying", "not pretending"],
                "error_missing": "You must acknowledge the self-deception. Use 'lying', 'pretending', or 'telling myself'.",
                "error_denial": "Procrastination always involves self-deception. What's the lie?",
            },
        ]

    def should_show_challenge(self, context="studying"):
        """
        Determine if a challenge should be shown.

        Args:
            context: "studying" or "wasting"

        Returns:
            bool: True if challenge should appear
        """
        if context == "studying":
            freq = self.config.get("studying_challenge_frequency", 0.3)
        else:
            freq = self.config.get("wasting_challenge_frequency", 0.5)

        return random.random() < freq

    def get_challenge(self, context="studying"):
        """
        Get a random challenge appropriate for the context.

        Args:
            context: "studying" or "wasting"

        Returns:
            dict: Challenge configuration or None if no challenge
        """
        if not self.should_show_challenge(context):
            return None

        if context == "studying":
            pool = self.studying_challenges
            # Filter by individual challenge settings
            pool = [
                c for c in pool
                if self.config.get(f"challenge_studying_{c['id']}_enabled", True)
            ]
        else:
            pool = self.wasting_challenges
            # Filter by individual challenge settings
            pool = [
                c for c in pool
                if self.config.get(f"challenge_wasting_{c['id']}_enabled", True)
            ]

        # If the user disabled every challenge type, don't show any challenge
        if not pool:
            return None

        return random.choice(pool)

    def validate_challenge_response(self, response, challenge):
        """
        Validate a response against a challenge's requirements.

        Args:
            response: User's text response
            challenge: Challenge dictionary

        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        response = (response or "").strip()
        response_lower = response.lower()

        # Check minimum length
        min_chars = self.config.get("challenge_min_total_length", 20)
        if len(response) < min_chars:
            return False, f"Response too short. Need at least {min_chars} characters."

        # Check minimum word count
        words = [w for w in response.split() if len(w) > 1]
        min_words = challenge.get("min_words", self.config.get("challenge_min_words", 5))
        if len(words) < min_words:
            return False, f"Response too short. Need at least {min_words} words."

        # Check required words
        required_words = challenge.get("required_words", [])
        required_mode = challenge.get("required_word_mode", "any")

        if required_mode == "any":
            # Need at least one required word
            if not any(word in response_lower for word in required_words):
                return False, challenge.get("error_missing", f"Must include one of: {', '.join(required_words)}")
        elif required_mode == "all":
            # Need all required words
            missing = [word for word in required_words if word not in response_lower]
            if missing:
                return False, challenge.get("error_missing", f"Must include: {', '.join(missing)}")

        # Check banned vague words
        banned_vague = challenge.get("banned_vague", [])
        for vague in banned_vague:
            if vague in response_lower:
                return False, challenge.get("error_vague", f"'{vague}' is too vague. Be more specific.")

        # Check banned phrases
        banned_phrases = challenge.get("banned_phrases", [])
        for phrase in banned_phrases:
            if phrase in response_lower:
                return False, challenge.get("error_generic", f"'{phrase}' is too generic. Be more specific.")

        # Check banned weak words (for commitment challenges)
        banned_weak = challenge.get("banned_weak", [])
        for weak in banned_weak:
            if weak in response_lower:
                return False, challenge.get("error_weak", f"Don't use '{weak}'. Make a definite commitment.")

        # Check for contrast (for "should" challenge)
        if challenge.get("must_show_contrast"):
            has_contrast = ("instead" in response_lower or
                          "but" in response_lower or
                          ("not" in response_lower and "should" in response_lower))
            if not has_contrast:
                return False, challenge.get("error_no_contrast", "Must show contrast between what you're doing and what you should do.")

        # Check for denial patterns
        for req_word in required_words:
            denial_patterns = [f"not {req_word}", f"no {req_word}", f"don't {req_word}"]
            for denial in denial_patterns:
                if denial in response_lower:
                    return False, challenge.get("error_denial", f"Don't deny it. Acknowledge the truth using '{req_word}'.")

        # Additional validation: can't ONLY be the required word (DISABLED - too strict)
        # if len(words) <= 2 and any(word in response_lower for word in required_words):
        #     return False, "You can't just type the required word. Explain fully."

        # All checks passed
        return True, None

    def get_challenge_hint(self, challenge):
        """
        Get a helpful hint for a challenge.

        Args:
            challenge: Challenge dictionary

        Returns:
            str: Hint text
        """
        hints = {
            "learning_specificity": "Example: 'I'm learning how to solve quadratic equations in algebra'",
            "goal_connection": "Example: 'My goal is to pass Friday's chemistry exam'",
            "will_commitment": "Example: 'I will finish reading chapter 3 and answer the review questions'",
            "output_expectation": "Example: 'I'll have completed 10 practice problems from section 4.2'",
            "wasting_acknowledgment": "Example: 'I'm wasting my last chance to prepare before tomorrow's test'",
            "should_gap": "Example: 'Scrolling Reddit instead of the essay I should be writing'",
            "because_reasoning": "Example: 'Because starting the assignment feels overwhelming and scary'",
            "hour_projection": "Example: 'In another hour I'll have zero time left and will panic'",
            "tomorrow_regret": "Example: 'Tomorrow I'll regret not using these 2 free hours to study'",
            "fear_acknowledgment": "Example: 'I'm afraid I'll fail even if I study hard'",
            "lying_confrontation": "Example: 'I'm lying to myself that I'll do it later tonight'",
        }
        return hints.get(challenge.get("id"), "")


def create_challenge_system(settings):
    """
    Create a challenge system from application settings.

    Args:
        settings: Application settings dictionary

    Returns:
        ChallengeSystem instance
    """
    config = {
        "studying_challenge_frequency": settings.get("challenge_studying_frequency", 0.3),
        "wasting_challenge_frequency": settings.get("challenge_wasting_frequency", 0.5),
        "challenge_min_words": settings.get("challenge_min_words", 5),
        "challenge_min_total_length": settings.get("challenge_min_total_length", 20),
        "allow_challenge_skip": settings.get("challenge_allow_skip", False),
    }

    # Carry through individual challenge toggles so disabling them actually removes them from the pool
    for cid in [
        "learning_specificity",
        "goal_connection",
        "will_commitment",
        "output_expectation",
    ]:
        config[f"challenge_studying_{cid}_enabled"] = settings.get(f"challenge_studying_{cid}_enabled", True)

    for cid in [
        "wasting_acknowledgment",
        "should_gap",
        "because_reasoning",
        "hour_projection",
        "tomorrow_regret",
        "fear_acknowledgment",
        "lying_confrontation",
    ]:
        config[f"challenge_wasting_{cid}_enabled"] = settings.get(f"challenge_wasting_{cid}_enabled", True)

    return ChallengeSystem(config)
