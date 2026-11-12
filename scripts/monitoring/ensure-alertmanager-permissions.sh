#!/usr/bin/env bash
set -euo pipefail

# Alertmanager's official image runs as nobody (65534). Config files copied by
# a root-owned sync job can otherwise inherit mode 0600 and make the container
# fail before it can load the configuration.
monitoring_root="${MONITORING_ROOT:-/opt/monitoring}"
active_config="${monitoring_root}/config/alertmanager/active.yml"
slack_secret="${monitoring_root}/secrets/slack_webhook_url"

if [[ ! -f "${active_config}" ]]; then
  echo "Alertmanager config not found: ${active_config}" >&2
  exit 1
fi

chown 65534:65534 "${active_config}"
chmod 0440 "${active_config}"

if [[ -f "${slack_secret}" ]]; then
  chown 65534:65534 "${slack_secret}"
  chmod 0400 "${slack_secret}"
fi

echo "Alertmanager config permissions repaired: ${active_config}"
