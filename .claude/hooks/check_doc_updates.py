"""PostToolUse hook for the AI-Agent-Orchestration-HW2 project.

Fires after Write/Edit. Reminds Claude to update docs/TODO.md, README.md,
and docs/PROMPTS.md when a code or config file is touched. Filters out
edits to documentation, settings, and gitignore (which would be noisy).

Reads tool input JSON on stdin; emits hookSpecificOutput JSON to stdout
only when the edited file matches the trigger pattern.
"""

import json
import re
import sys

REMINDER = (
    "\U0001f6a8 You just edited a code/config file. Per CLAUDE.md non-negotiables: "
    "check whether docs/TODO.md (mark tasks complete), README.md (status section), "
    "or docs/PROMPTS.md need updates BEFORE claiming this chunk is done."
)

EXCLUDE = re.compile(r"(^|/)docs/|(^|/)README\.md$|(^|/)\.claude/|(^|/)\.gitignore$", re.I)
INCLUDE = re.compile(r"(^|/)(src|config|tests)/|(^|/)pyproject\.toml$", re.I)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    file_path = ((data.get("tool_input") or {}).get("file_path") or "").replace("\\", "/")
    if not file_path or EXCLUDE.search(file_path) or not INCLUDE.search(file_path):
        return

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": REMINDER,
        }
    }
    json.dump(output, sys.stdout)


if __name__ == "__main__":
    main()
