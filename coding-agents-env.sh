# Coding-agent CLIs — source this before use:  source ~/workspace/bin/coding-agents-env.sh
# Installed 2026-10-10 into ~/workspace/.npm-global (npm prefix), survives VM restarts.
export PATH="$HOME/workspace/.npm-global/bin:$PATH"

# Gemini CLI: API-key auth (no browser needed)
export GEMINI_API_KEY="$(cat "$HOME/workspace/keys/GEMINI_KEY")"
export GEMINI_CLI_TRUST_WORKSPACE=true   # headless/non-tty use

# GitHub Copilot CLI: authenticated via device-code flow (token lands in ~/.copilot/).
# NOTE: the GITHUB_PAT lacks the "Copilot Requests" permission, so
# `copilot login --with-token` and COPILOT_GITHUB_TOKEN do NOT work.
# Re-auth:  copilot login --device-code   (then enter code at github.com/login/device)

# gh CLI is authed as mfspxz via the PAT (gh auth login --with-token).
