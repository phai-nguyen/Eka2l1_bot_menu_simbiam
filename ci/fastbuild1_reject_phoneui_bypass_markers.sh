#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! -f "$1" ]]; then
  echo "usage: fastbuild1_reject_phoneui_bypass_markers.sh <strings-file>" >&2
  exit 2
fi

strings_file="$1"
for forbidden_marker in \
  '[NBOOT2][PHONEUI_CONE14_CONTINUE_B88]' \
  '[NBOOT2][PHONEUI_FAILSTATE_BYPASS_B89]'; do
  if grep -Fq "$forbidden_marker" "$strings_file"; then
    echo "FASTBUILD1-BINARY-GATE: forbidden marker found: $forbidden_marker" >&2
    exit 1
  else
    grep_status=$?
    if [[ $grep_status -ne 1 ]]; then
      echo "FASTBUILD1-BINARY-GATE: could not inspect binary strings (grep exit $grep_status)" >&2
      exit "$grep_status"
    fi
  fi
done

echo "FASTBUILD1-BINARY-GATE: no PhoneUI startup bypass markers"
