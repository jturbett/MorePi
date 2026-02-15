# Local secrets folder

Store local runtime secret files in this folder.

Example file:

- `secrets/discord.txt` containing only the Discord webhook URL value.
- `secrets/farmbot_authorization_token.json` containing your Farmbot token/secret.

`secrets/*.txt` and `secrets/*.json` are ignored by git.


These are host-side files in your repo working directory. Docker mounts them to `/run/secrets/...` inside the container.

- `secrets/unifi_protect_api_key.txt` containing your UniFi Protect webhook API key.
- `secrets/unifi_key` containing your UniFi Protect webhook API key (simple default filename).

For the UniFi key, set either:
- `UNIFI_PROTECT_API_KEY_FILE=/run/secrets/unifi_protect_api_key.txt` (recommended),
- `UNIFI_PROTECT_API_KEY=<value>`, or
- place the key in `secrets/unifi_key` for repo-local fallback.

