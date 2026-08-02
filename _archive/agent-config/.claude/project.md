# DEVRECON Project Context

## Project Overview
This is the Current workspace within DEVRECON, containing the FocusCheck application and development tools.

## Key Components
- **FocusCheck**: Python-based focus tracking application with system tray integration
- **main.py**: Application entry point handling CLI args and startup
- **Node.js components**: Package management and tooling

## Development Workflow

### AI Assistant Integration

#### Codex Pro Integration
This project has access to **Codex Pro** (GPT-5-Codex with extended reasoning), which should be used as a complementary validation and analysis tool.

**When to Use Codex:**
- **Validation**: Before implementing complex features, validate architectural decisions
- **Bulk Analysis**: When analyzing 20+ files or large codebases
- **Context Overflow**: When files exceed Claude's context limits (Codex has 272k window)
- **Second Opinion**: When uncertain about approach or design decisions
- **Extended Reasoning**: For complex problems requiring deep thinking chains

**Key Codex Commands:**
```bash
# Validation workflow
codex exec --skip-git-repo-check "Review this approach: [description]. Find issues and suggest improvements."

# Bulk analysis
codex exec --skip-git-repo-check --json "Analyze all Python files and [task]"

# Extended reasoning
codex exec --skip-git-repo-check -m gpt-5-codex "Complex problem: [description]"

# Resume long tasks
codex exec resume --last "Continue with [next step]"
```

**Important Notes:**
- Codex has **unlimited usage** - use liberally
- Always include `--skip-git-repo-check` flag (not a git repo)
- Use `--json` for structured output
- Use `-m gpt-4o` for speed, `-m gpt-5-codex` for depth
- See `.claude/skills/codex-validator.md` for comprehensive guide

**Codex Configuration:**
- Version: codex-cli 0.38.0
- Location: `C:\Users\singh\AppData\Roaming\npm\codex`
- Authentication: Logged in via ChatGPT
- Model: gpt-5-codex (default) with 272k context window

### Recommended Workflow
1. **Plan** - Claude Code analyzes requirements
2. **Validate** - Use Codex to review approach before implementation
3. **Implement** - Claude Code writes production-quality code
4. **Review** - Optional Codex validation of complex implementations

## Environment Details
- **Platform**: Windows (win32)
- **Working Directory**: `C:\Users\singh\Documents\DEVRECON\Current`
- **Not a Git Repository**: Use `--skip-git-repo-check` with Codex

## Special Considerations
- This workspace has custom permission settings in `.claude/settings.local.json`
- Codex commands are pre-approved for common operations
- Bash commands use mixed Windows/Unix syntax depending on context
