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
| `MAX_POSTS_PER_RUN` | Integer | `6` | Maximum number of Bluesky posts allowed per polling run. Prevents massive spam burst flags when recovering from outages. |
| `POST_DELAY_SECONDS` | Integer | `5` | Courtesy delay in seconds between consecutive post publications within the same cycle. |
| `LINK_DESTINATION` | String | `tmdb` | Target destination for external card embeds. Values: `tmdb` (The Movie Database), `wetrakr`, `simkl`, or `imdb`. |
| `TZ` | String | `Europe/Madrid` | System timezone. Essential for accurately calculating time-of-day phrases, weekdays, and reporting windows. |

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

Create your `compose.yaml` (using modern Compose v2 specification):

```yaml
services:
  bsky-media-scrobbler:
    build: .
    image: bsky-media-scrobbler:latest
    container_name: bsky-media-scrobbler
    restart: unless-stopped
    mem_limit: 256m
    environment:
      - TZ=Europe/Madrid
      - PYTHONUNBUFFERED=1
      - DRY_RUN=${DRY_RUN:-false}
      - TRACKER_PROVIDER=${TRACKER_PROVIDER:-simkl}
      - SIMKL_CLIENT_ID=${SIMKL_CLIENT_ID}
      - SIMKL_USER_TOKEN=${SIMKL_USER_TOKEN}
      - WETRAKR_CLIENT_ID=${WETRAKR_CLIENT_ID}
      - WETRAKR_CLIENT_SECRET=${WETRAKR_CLIENT_SECRET}
      - BSKY_HANDLE=${BSKY_HANDLE}
      - BSKY_APP_PASSWORD=${BSKY_APP_PASSWORD}
      - BSKY_LANG=${BSKY_LANG:-en}
      - POLL_INTERVAL_MINUTES=${POLL_INTERVAL_MINUTES:-90}
      - MAX_POSTS_PER_RUN=${MAX_POSTS_PER_RUN:-6}
      - POST_DELAY_SECONDS=${POST_DELAY_SECONDS:-5}
      - LINK_DESTINATION=${LINK_DESTINATION:-tmdb}
    volumes:
      - ./app:/app
      - ./data:/data
```

> **Note for advanced setups (Reverse Proxy / Dockge):** If you use a shared bridge network (e.g. Cloudflare Tunnel, Nginx Proxy Manager, or Traefik), simply attach your `networks:` block to the service. For 99% of users, the standard configuration above works out of the box.
