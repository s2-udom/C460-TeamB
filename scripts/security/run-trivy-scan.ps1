<##
Run the pinned Trivy repository scan on a Windows Jenkins agent.

The script fails closed when Trivy is missing, the installed version does not
match ci/trivy/version.txt, the scan cannot run, or critical findings exist.
Reports are written to the workspace so Jenkins can archive them in post.
##>
[CmdletBinding()]
param(
    [string]$Target = '.',
    [string]$VersionFile = 'ci/trivy/version.txt',
    [string]$TextReport = 'trivy-repository-report.txt',
    [string]$CriticalReport = 'trivy-critical-findings.json',
    [string]$VersionReport = 'trivy-version.txt'
)

$ErrorActionPreference = 'Stop'

function Stop-Scan([string]$Message, [int]$Code = 2) {
    # Override the script-wide Stop preference so the requested exit code is
    # returned to Jenkins instead of being replaced by a PowerShell exception.
    Write-Error $Message -ErrorAction Continue
    exit $Code
}

if (-not (Test-Path -LiteralPath $VersionFile -PathType Leaf)) {
    Stop-Scan "Trivy version file was not found: $VersionFile"
}

$expectedVersion = (Get-Content -LiteralPath $VersionFile -Raw).Trim()
if ([string]::IsNullOrWhiteSpace($expectedVersion)) {
    Stop-Scan "Trivy version file is empty: $VersionFile"
}

$trivyCommand = Get-Command trivy.exe -ErrorAction SilentlyContinue
if ($null -eq $trivyCommand) {
    $trivyCommand = Get-Command trivy -ErrorAction SilentlyContinue
}
if ($null -eq $trivyCommand) {
    Stop-Scan "Trivy was not found on PATH. Install the pinned version from ci/trivy/README.md." 127
}

$trivyPath = if ($trivyCommand.Source) { $trivyCommand.Source } else { $trivyCommand.Path }
$versionOutput = @(& $trivyPath --version 2>&1)
$versionExit = $LASTEXITCODE
$versionOutput | Set-Content -LiteralPath $VersionReport
if ($versionExit -ne 0) {
    Stop-Scan "Trivy could not report its version. Exit code: $versionExit" $versionExit
}

$versionText = $versionOutput -join "`n"
$versionPattern = '(?m)Version:\s*v?' + [regex]::Escape($expectedVersion) + '\b'
if ($versionText -notmatch $versionPattern) {
    Stop-Scan "Trivy version mismatch. Expected $expectedVersion; found:`n$versionText"
}

$commonArguments = @(
    'fs',
    '--scanners', 'vuln,secret,misconfig',
    '--include-dev-deps',
    '--skip-dirs', '.git',
    '--skip-dirs', 'node_modules',
    '--skip-dirs', '.frontend-lint',
    '--skip-dirs', '.frontend-lint-*',
    '--no-progress',
    '--timeout', '10m'
)

# Produce a readable report for review. This report includes all severities,
# while the separate critical scan below enforces the pipeline policy.
& $trivyPath @commonArguments `
    '--severity' 'UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL' `
    '--format' 'table' `
    '--output' $TextReport `
    '--exit-code' '0' `
    $Target
$fullScanExit = $LASTEXITCODE
if ($fullScanExit -ne 0) {
    Stop-Scan "Trivy repository scan could not complete. Exit code: $fullScanExit" $fullScanExit
}

# Run a second, focused scan so the Jenkins build fails specifically for
# critical findings without hiding lower-severity findings in the full report.
& $trivyPath @commonArguments `
    '--severity' 'CRITICAL' `
    '--format' 'json' `
    '--output' $CriticalReport `
    '--exit-code' '1' `
    $Target
$criticalScanExit = $LASTEXITCODE
if ($criticalScanExit -eq 1) {
    Stop-Scan "Trivy found one or more CRITICAL repository findings. Review $CriticalReport and $TextReport." 1
}
if ($criticalScanExit -ne 0) {
    Stop-Scan "Trivy critical-severity scan could not complete. Exit code: $criticalScanExit" $criticalScanExit
}

Write-Host "Trivy repository scan completed with no CRITICAL findings."
exit 0
