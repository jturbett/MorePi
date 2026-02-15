#!/bin/bash
set -euo pipefail

ENV_FILE="$HOME/compose-stack/.env"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# default to allowing self-signed unless explicitly disabled in .env
UNIFI_INSECURE="${UNIFI_INSECURE:-1}"
CURL_TLS=()
[[ "$UNIFI_INSECURE" == "1" ]] && CURL_TLS+=(-k)

OUT_DIR="$HOME/compose-stack/services/nginx/html"
OUT_FILE="$OUT_DIR/unifi_events.json"

mkdir -p "$OUT_DIR"

echo "📡 Fetching 25 most recent events from ${NVR_URL:-<unset>} ..."
TMP="$(mktemp)"
if ! curl -sSf "${CURL_TLS[@]}" -H "Authorization: Bearer ${API_TOKEN:-}" \
  "${NVR_URL:-}/proxy/protect/api/events?limit=25&end=$(date +%s)000" \
  -o "$TMP"; then
  echo "⚠️ curl failed. Check NVR_URL/API_TOKEN or network." >&2
  rm -f "$TMP"
  exit 1
fi

if ! jq '(.items // .) | .[0:25]' "$TMP" > "$OUT_FILE"; then
  echo "⚠️ jq parse failed. First 200 bytes of response:" >&2
  head -c 200 "$TMP" >&2; echo >&2
  rm -f "$TMP"
  exit 1
fi

rm -f "$TMP"
echo "✅ Wrote events to $OUT_FILE"

