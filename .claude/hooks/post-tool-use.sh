#!/bin/bash
# Claude Code hook: runs after Edit/Write on backend Python files.
# Checks syntax so Claude Code catches import errors before deployment.

TOOL_NAME="${CLAUDE_TOOL_NAME:-}"
FILE_PATH="${CLAUDE_FILE_PATH:-}"

# Only act on backend Python edits
if [[ "$TOOL_NAME" =~ ^(Edit|Write)$ ]] && [[ "$FILE_PATH" == *"/backend/"* ]] && [[ "$FILE_PATH" == *.py ]]; then
    python3 -c "
import ast, sys
try:
    with open('$FILE_PATH') as f:
        ast.parse(f.read())
    print(f'[hook] Syntax OK: $FILE_PATH')
except SyntaxError as e:
    print(f'[hook] SYNTAX ERROR in $FILE_PATH: {e}', file=sys.stderr)
    sys.exit(1)
"
fi
