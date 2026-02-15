#!/usr/bin/env bash
set -euo pipefail

GRAYLOG_URL="${GRAYLOG_URL:-http://127.0.0.1:9001}"
GRAYLOG_USER="${GRAYLOG_USER:-admin}"
GRAYLOG_PASS="${GRAYLOG_PASS:-changeme}"
INPUT_ID="${INPUT_ID:-6957fd5e4cbb7448f6ea041e}"
JSON_FILE="${JSON_FILE:-$(dirname "$0")/udm_extractors.json}"

command -v jq >/dev/null 2>&1 || { echo "jq is required. Install: sudo apt-get install -y jq"; exit 1; }

echo "Importing extractors into input: ${INPUT_ID}"
echo "Graylog: ${GRAYLOG_URL}"

# sanity check
curl -sS -u "${GRAYLOG_USER}:${GRAYLOG_PASS}" \
  -H 'X-Requested-By: cli' \
  "${GRAYLOG_URL}/api/system" >/dev/null || {
    echo "ERROR: Cannot reach Graylog API or auth failed."
    echo "Tip: export GRAYLOG_PASS='your-admin-password' and try again."
    exit 1
  }

# create each extractor
jq -c '.extractors[]' "${JSON_FILE}" | while read -r extractor; do
  title="$(echo "$extractor" | jq -r '.title')"
  echo " - creating: ${title}"
  curl -sS -u "${GRAYLOG_USER}:${GRAYLOG_PASS}" \
    -H 'Content-Type: application/json' \
    -H 'X-Requested-By: cli' \
    -X POST \
    -d "${extractor}" \
    "${GRAYLOG_URL}/api/system/inputs/${INPUT_ID}/extractors" >/dev/null
done

echo "Done."

