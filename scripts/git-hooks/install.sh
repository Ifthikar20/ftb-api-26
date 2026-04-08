#!/usr/bin/env bash
#
# Install project git hooks into the local .git/hooks directory.
# Run from anywhere inside the repository.
#

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$REPO_ROOT" ]; then
    echo "Error: not inside a git repository."
    exit 1
fi

HOOKS_SRC="$REPO_ROOT/scripts/git-hooks"
HOOKS_DST="$REPO_ROOT/.git/hooks"

for hook in "$HOOKS_SRC"/*; do
    hook_name=$(basename "$hook")

    # Skip this installer script itself
    if [ "$hook_name" = "install.sh" ]; then
        continue
    fi

    cp "$hook" "$HOOKS_DST/$hook_name"
    chmod +x "$HOOKS_DST/$hook_name"
    echo "Installed $hook_name hook."
done

echo "All hooks installed successfully."
