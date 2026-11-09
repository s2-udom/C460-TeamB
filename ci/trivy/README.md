# Trivy repository scanning

This project uses Trivy filesystem scanning against the checked-out repository.
The pinned version is recorded in `ci/trivy/version.txt`. Updating Trivy is an
intentional change: update that file, test the scan, and record the change in the
pull request.

The scan checks vulnerabilities, secrets, and supported repository
misconfigurations. Development dependencies are included, while generated
`node_modules` and temporary frontend-lint directories are skipped.

The scan creates these Jenkins artifacts:

- `trivy-repository-report.txt`: readable report containing all severities.
- `trivy-critical-findings.json`: machine-readable critical-severity gate report.
- `trivy-version.txt`: the Trivy version used for the run.

The build fails when the pinned Trivy version is missing, the scan cannot run, or
critical findings are detected. AWS deployment remains disabled in this local
prototype pipeline.

## Install the pinned version on the Windows Jenkins agent

1. Download the `Windows-64bit` ZIP for `v0.76.2` from the official [Trivy
   release page](https://github.com/aquasecurity/trivy/releases/tag/v0.76.2).
2. Extract `trivy.exe` to a stable directory such as `C:\Tools\Trivy`.
3. Add that directory to the Windows `PATH` for the account running the Jenkins
   agent.
4. Restart the Jenkins agent so it receives the updated `PATH`.
5. In the same account's terminal, confirm `trivy --version` reports `0.76.2`.

The Jenkins stage intentionally does not download tools during a build. This
keeps the build reproducible and makes an incorrectly configured agent visible.
