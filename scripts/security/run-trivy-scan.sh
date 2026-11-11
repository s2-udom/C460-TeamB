#!/usr/bin/env bash
# Run the pinned Trivy repository scan on a Linux Jenkins agent.
# The Windows Jenkins agent uses the matching .ps1 script beside this file.

set -u

target="${1:-.}"
version_file="ci/trivy/version.txt"
text_report="trivy-repository-report.txt"
critical_report="trivy-critical-findings.json"
version_report="trivy-version.txt"

fail() {
    echo "ERROR: $1" >&2
    exit "${2:-2}"
}

[[ -f "$version_file" ]] || fail "Trivy version file was not found: $version_file"
expected_version="$(tr -d '[:space:]' < "$version_file")"
[[ -n "$expected_version" ]] || fail "Trivy version file is empty: $version_file"

command -v trivy >/dev/null 2>&1 || fail "Trivy was not found on PATH. Install the pinned version from ci/trivy/README.md" 127

set +e
version_output="$(trivy --version 2>&1)"
version_exit=$?
set -e
printf '%s\n' "$version_output" > "$version_report"
[[ "$version_exit" -eq 0 ]] || fail "Trivy could not report its version. Exit code: $version_exit" "$version_exit"
case "$version_output" in
    *"Version: $expected_version"*|*"Version: v$expected_version"*) ;;
    *) fail "Trivy version mismatch. Expected $expected_version; found:\n$version_output" ;;
esac

common_args=(
    fs
    --scanners vuln,secret,misconfig
    --include-dev-deps
    --skip-dirs .git
    --skip-dirs node_modules
    --skip-dirs .frontend-lint
    --skip-dirs '.frontend-lint-*'
    --no-progress
    --timeout 10m
)

# Keep all severities in the readable report. The focused scan below enforces
# the critical-only build policy.
set +e
trivy "${common_args[@]}" \
    --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL \
    --format table \
    --output "$text_report" \
    --exit-code 0 \
    "$target"
full_scan_exit=$?
set -e
[[ "$full_scan_exit" -eq 0 ]] || fail "Trivy repository scan could not complete. Exit code: $full_scan_exit" "$full_scan_exit"

set +e
trivy "${common_args[@]}" \
    --severity CRITICAL \
    --format json \
    --output "$critical_report" \
    --exit-code 1 \
    "$target"
critical_scan_exit=$?
set -e
if [[ "$critical_scan_exit" -eq 1 ]]; then
    fail "Trivy found one or more CRITICAL repository findings. Review $critical_report and $text_report" 1
fi
[[ "$critical_scan_exit" -eq 0 ]] || fail "Trivy critical-severity scan could not complete. Exit code: $critical_scan_exit" "$critical_scan_exit"

echo "Trivy repository scan completed with no CRITICAL findings."
