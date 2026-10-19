#!/bin/sh
# Checks out Matt's Eagle Homebrew at the pinned commit into vendor/eagle-homebrew (never edited locally).
set -eu
HOST_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ROOT=$(CDPATH= cd -- "$HOST_DIR/../.." && pwd)
. "$HOST_DIR/eagle-homebrew.pin"
TARGET="$ROOT/vendor/eagle-homebrew"
if [ ! -d "$TARGET/.git" ]; then
  mkdir -p "$ROOT/vendor"
  git clone --quiet "$EAGLE_HOMEBREW_REPO" "$TARGET"
fi
if ! git -C "$TARGET" cat-file -e "$EAGLE_HOMEBREW_COMMIT^{commit}" 2>/dev/null; then
  git -C "$TARGET" fetch --quiet "$EAGLE_HOMEBREW_REPO" "$EAGLE_HOMEBREW_COMMIT" 2>/dev/null || git -C "$TARGET" fetch --quiet "$EAGLE_HOMEBREW_REPO"
fi
git -C "$TARGET" checkout --quiet --detach "$EAGLE_HOMEBREW_COMMIT"
ACTUAL=$(git -C "$TARGET" rev-parse HEAD)
if [ "$ACTUAL" != "$EAGLE_HOMEBREW_COMMIT" ]; then
  echo "vendor/eagle-homebrew is at $ACTUAL, expected $EAGLE_HOMEBREW_COMMIT" >&2
  exit 1
fi
if [ -n "$(git -C "$TARGET" status --porcelain)" ]; then
  echo "vendor/eagle-homebrew has local changes; Matt's code is never edited here" >&2
  exit 1
fi
echo "Eagle Homebrew $EAGLE_HOMEBREW_COMMIT ready in vendor/eagle-homebrew"
