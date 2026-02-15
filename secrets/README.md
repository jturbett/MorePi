# Local secrets folder

Store local runtime secret files in this folder.

Example file:

- `secrets/discord.txt` containing only the Discord webhook URL value.
- `secrets/farmbot_authorization_token.json` containing your Farmbot token/secret.

`secrets/*.txt` and `secrets/*.json` are ignored by git.


These are host-side files in your repo working directory. Docker mounts them to `/run/secrets/...` inside the container.
