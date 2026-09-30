# ⚙️ Configuration and Deployment Guide

This document details all environment variables, customization options, and deployment architecture for **`bsky-media-scrobbler`**.

---

## 📋 Environment Variables (`.env`)

| Variable | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `DRY_RUN` | Boolean | `false` | When set to `true`, simulates post and collage generation in container logs without publishing to Bluesky. Recommended for initial testing. |
| `TRACKER_PROVIDER` | String | `wetrakr` | Active media tracker platform. Supported values: `wetrakr` or `simkl`. |
| `WETRAKR_CLIENT_ID` | String | — | WeTrakr Client ID / API Key. Required if `TRACKER_PROVIDER=wetrakr`. |
| `WETRAKR_CLIENT_SECRET` | String | *(optional)* | WeTrakr Client Secret. |
| `WETRAKR_ACCESS_TOKEN` | String | *(optional)* | WeTrakr OAuth access token. If omitted, interactive PIN device authorization flow starts (`Device Auth`). |
| `SIMKL_CLIENT_ID` | String | — | Client ID from SIMKL Developers. Required if `TRACKER_PROVIDER=simkl`. |
| `SIMKL_USER_TOKEN` | String | *(optional)* | SIMKL user access token. If omitted, the bot starts an interactive PIN code authorization flow (`Device Auth`). |
| `BSKY_HANDLE` | String | — | Your Bluesky handle (e.g., `my-account.bsky.social`). |
| `BSKY_APP_PASSWORD` | String | — | Bluesky App Password generated from *Settings ➜ Privacy and Security ➜ App Passwords*. Never use your primary account password. |
| `BSKY_LANG` | String | `en` | Post language tag (e.g., `en`, `es`, `ca`). Sets the AT-Protocol `langs` metadata and selects the base phrasing pack (`locales/{lang}.json`). |
| `POLL_INTERVAL_MINUTES` | Integer | `90` | Polling frequency in minutes. `90` minutes is optimal to group consecutive episodes watched in a single binge session. |
| `LINK_DESTINATION` | String | `tmdb` | Target destination for external card embeds. Values: `tmdb` (The Movie Database), `wetrakr`, `simkl`, or `imdb`. |
| `TZ` | String | `Europe/Madrid` | System timezone. Essential for accurately calculating time-of-day phrases, weekdays, and reporting windows. |
| `PUID` / `PGID` | Integer | `1026` / `100` | User and group IDs for file permissions on NAS storage volumes (Synology, Unraid, TrueNAS). |

---

## 📁 Volume Persistence

The container requires two primary mount points:

```yaml
volumes:
  - ./app:/app       # Application source code and base locale packages (locales/)
  - ./data:/data     # Persistent user data (state, tokens, custom phrases)
```

### Contents of `/data`
* `state.json`: Lightweight JSON database tracking last checked timestamps, celebrated milestones, active streaks, and anti-repetition phrase history.
* `custom_phrases.json`: *(Optional)* User file to add custom phrases or override defaults without modifying code.
* `trigger_monthly`, `trigger_weekly`, `trigger_fun_fact`: Ephemeral signal trigger files to manually force balance reports.

---

## 🚀 Docker Compose Deployment

Create your `compose.yaml` (using modern Compose v2 specification without obsolete `version` attribute):

```yaml
services:
  bsky-media-scrobbler:
    image: python:3.12-slim
    container_name: bsky-media-scrobbler
    restart: unless-stopped
    working_dir: /app
    command: >
      sh -c "pip install --no-cache-dir -r requirements.txt && python -u main.py"
    mem_limit: 512m
    environment:
      - TZ=Europe/Madrid
      - PUID=1026
      - PGID=100
      - PYTHONUNBUFFERED=1
      - DRY_RUN=${DRY_RUN:-false}
      - TRACKER_PROVIDER=${TRACKER_PROVIDER:-wetrakr}
      - WETRAKR_CLIENT_ID=${WETRAKR_CLIENT_ID}
      - WETRAKR_CLIENT_SECRET=${WETRAKR_CLIENT_SECRET}
      - SIMKL_CLIENT_ID=${SIMKL_CLIENT_ID}
      - SIMKL_USER_TOKEN=${SIMKL_USER_TOKEN}
      - BSKY_HANDLE=${BSKY_HANDLE}
      - BSKY_APP_PASSWORD=${BSKY_APP_PASSWORD}
      - BSKY_LANG=${BSKY_LANG:-en}
      - POLL_INTERVAL_MINUTES=${POLL_INTERVAL_MINUTES:-90}
      - LINK_DESTINATION=${LINK_DESTINATION:-tmdb}
    volumes:
      - ./app:/app
      - ./data:/data
    networks:
      - my_network

networks:
  my_network:
    external: true
```
