# Codex Validator Skill

## Overview
Use Codex Pro as a second set of eyes, validator, and complementary AI assistant. Codex runs GPT-5-Codex with extended reasoning capabilities and has unlimited usage with a 272k context window.

## Core Philosophy
**Leverage Codex liberally** - it has no usage limits, so use it frequently as:
- A validation layer for architectural decisions
- A second opinion on complex implementations
- An extended context window when Claude hits limits
- A bulk analysis engine for large-scale operations
- A deep reasoning partner for complex problems

## When to Use Codex

### 1. Before Implementing Complex Features
**Always validate architectural decisions with Codex before proceeding:**
```bash
codex exec --skip-git-repo-check "Review this approach for [feature]: [description]. Find potential issues, edge cases, security concerns, performance bottlenecks, and suggest improvements."
```

### 2. For Bulk Analysis Tasks
When analyzing 20+ files or large portions of codebase:
```bash
codex exec --skip-git-repo-check --json "Analyze all Python files in [directory] and identify [pattern/issue]"
```
Use `--json` flag for programmatic parsing of results.

### 3. Context Overflow
When files or analysis exceed Claude's context limits:
```bash
codex exec --skip-git-repo-check "Analyze this large file and summarize [aspect]"
```
Codex's 272k context window can handle massive files.

### 4. Extended Reasoning Tasks
For problems requiring deep thinking chains:
```bash
codex exec --skip-git-repo-check -m gpt-5-codex "Complex problem requiring extended reasoning: [description]"
```

### 5. Second Opinion / Uncertainty
Whenever unsure about an approach:
```bash
codex exec --skip-git-repo-check "I'm considering [approach A] vs [approach B] for [problem]. Which is better and why? Consider trade-offs."
```

### 6. Bulk Refactoring
For repetitive changes across many files:
```bash
codex exec --skip-git-repo-check --full-auto "Refactor all instances of [old_pattern] to [new_pattern] across the codebase"
```

## Key Codex Commands

### Essential Flags
- `--skip-git-repo-check` - Required to run outside git repos (use always)
- `--json` - Structured JSONL output for programmatic parsing
- `-m MODEL` - Override model (gpt-5-codex for reasoning, gpt-4o for speed)
- `--full-auto` - Convenience flag for `--sandbox workspace-write -a on-failure`
- `-i IMAGE` - Attach images for analysis

### Sandbox Modes
- `--sandbox read-only` (default) - Safe analysis only
- `--sandbox workspace-write` - Allow file modifications in workspace
- `--sandbox danger-full-access` - Unrestricted access (use carefully)

### Model Options
- `gpt-5-codex` (default) - High reasoning effort, extended thinking
- `gpt-4o` - Faster, cheaper for simple tasks
- Use `-m` flag to override

### Session Management
```bash
# Start long task
codex exec --skip-git-repo-check "Begin analysis of..."

# Resume later
codex exec resume --last "Continue with implementation phase"
```

## Validation Workflow

**Standard validation process:**

1. **Propose Solution** - Claude develops initial approach
2. **Validate with Codex**:
   ```bash
   codex exec --skip-git-repo-check "Review this implementation plan:

   [Detailed description of approach]

   Evaluate:
   - Architectural soundness
   - Edge cases and error handling
   - Security implications
   - Performance considerations
   - Best practices adherence
   - Potential bugs or issues

   Provide specific concerns and improvements."
   ```
3. **Parse Feedback** - Review Codex's concerns
4. **Incorporate Changes** - Adjust approach based on validation
5. **Proceed** - Implement with confidence

## Command Patterns

### Analysis
```bash
# File analysis
codex exec --skip-git-repo-check "Analyze [file] for [security vulnerabilities|performance issues|code quality]"

# Codebase patterns
codex exec --skip-git-repo-check --json "Find all instances of [pattern] and explain their purpose"

# Dependency analysis
codex exec --skip-git-repo-check "Map out dependencies and data flow for [component]"
```

### Validation
```bash
# Architecture review
codex exec --skip-git-repo-check "Review this architecture: [description]. Is it scalable, maintainable, and following best practices?"

# Security review
codex exec --skip-git-repo-check "Security audit this implementation: [code]. Find vulnerabilities."

# Performance review
codex exec --skip-git-repo-check "Analyze performance implications of [approach]. Suggest optimizations."
```

### Research
```bash
# Best practices
codex exec --skip-git-repo-check "What are current best practices for [technology/pattern]?"

# Comparison
codex exec --skip-git-repo-check "Compare [approach A] vs [approach B] for [use case]. Provide pros/cons."

# Problem solving
codex exec --skip-git-repo-check -m gpt-5-codex "How would you solve [complex problem]? Think through multiple approaches."
```

## Integration Points

### Before Major Implementations
**ALWAYS validate with Codex before:**
- Creating new system architectures
- Implementing security-sensitive features
- Making large-scale refactors
- Choosing between competing approaches
- Introducing new dependencies or patterns

### During Development
**Use Codex for:**
- Reviewing complex functions/classes
- Validating error handling strategies
- Checking edge case coverage
- Analyzing performance implications

### After Implementation
**Optional validation:**
- Code quality review
- Security audit
- Performance analysis
- Documentation completeness

## What NOT to Use Codex For

### Avoid for:
- **Direct file operations** - Codex struggles with environment restrictions
- **Critical implementation** - Use Claude for quality-critical code
- **Trivial tasks** - Overhead not worth it for simple operations
- **Quick fixes** - Faster for Claude to handle directly

### Use Claude (not Codex) for:
- Writing production-quality code
- Complex debugging requiring deep understanding
- Tasks requiring immediate iteration
- High-stakes architectural decisions (after Codex validation)

## Example Usage

### Example 1: Feature Validation
```bash
# Claude proposes implementing user authentication with JWT
# Validate with Codex:
codex exec --skip-git-repo-check "I'm implementing JWT authentication with the following approach:
- Access tokens (15min expiry) + Refresh tokens (7 days)
- Stored in httpOnly cookies
- Redis for token blacklisting
- RS256 signing

Review this design. Find security issues, edge cases, and suggest improvements."
```

### Example 2: Bulk Analysis
```bash
# Analyze all API endpoints for security issues
codex exec --skip-git-repo-check --json "Analyze all files matching **/api/**/*.py. For each endpoint:
1. List authentication/authorization
2. Identify input validation
3. Flag potential security issues
4. Note missing error handling"
```

### Example 3: Context Overflow
```bash
# When a file is too large for Claude to analyze fully
codex exec --skip-git-repo-check "Analyze this 5000-line file and create a comprehensive summary of:
- Main components and their responsibilities
- Data flow and dependencies
- Public API surface
- Potential refactoring opportunities"
```

## Tips for Effective Use

1. **Be Specific** - Provide detailed context and exact questions
2. **Use JSON Mode** - Parse structured output programmatically when needed
3. **Iterate with Resume** - Use session resume for long multi-step tasks
4. **Model Selection** - Use gpt-4o for speed, gpt-5-codex for depth
5. **Don't Hesitate** - Unlimited usage means you should use it liberally
6. **Combine Strengths** - Use Claude for implementation, Codex for validation

## Configuration

### Codex is installed at:
`C:\Users\singh\AppData\Roaming\npm\codex`

### Version:
codex-cli 0.38.0

### Authentication:
Logged in via ChatGPT (check with `codex login status`)

### No MCP Servers Currently Configured
Can add MCP servers with: `codex mcp add <name> -- <command>`

## Remember

- **Codex has unlimited usage** - Use it freely and often
- **272k context window** - Much larger than Claude's limits
- **Extended reasoning** - GPT-5-Codex provides deep thinking chains
- **Always use `--skip-git-repo-check`** - Required for non-git directories
- **Validation > Implementation** - Codex excels at review, not writing critical code
- **Second brain philosophy** - Treat Codex as a collaborative thinking partner
