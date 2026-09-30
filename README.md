# 📺 Bluesky Media Scrobbler (`bsky-media-scrobbler`)

<p align="center">
  <b>Language:</b>
  <a href="README.md">🇬🇧 English</a> •
  <a href="README.es.md">🇪🇸 Español</a> •
  <a href="README.ca.md">🏴󠁥󠁳󠁣󠁴󠁿 Català</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue.svg?logo=python" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker" alt="Docker Ready" />
  <img src="https://img.shields.io/badge/Bluesky-AT%20Protocol-0085ff.svg?logo=bluesky" alt="Bluesky" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT License" />
</p>

An autonomous Python container for Docker that monitors your media activity on your favorite tracking platforms (**SIMKL**, **WeTrakr**) and publishes enriched scrobbles to **Bluesky** with **TMDB** external cards, high-definition poster collages, closed reporting periods, and daily viewing streak counters.

---

## ✨ Key Features

* 🔌 **Universal Multi-Tracker:** Native support for **SIMKL** and **WeTrakr** via the `TRACKER_PROVIDER` environment variable.
* 📦 **Smart Binge Grouping:** Automatically groups back-to-back episodes (e.g., `S01E01–E03`) into a single post to keep your Bluesky timeline uncluttered.
* 🎬 **Enriched Cards (TMDB):** Generates interactive external cards directed to The Movie Database with high-resolution poster artwork.
* ✍️ **Dynamic Phrasing & Native Multi-Language (i18n):**
  * Over 220 official phrases categorized by time of day, day of the week, binge volume, season finales, and plot milestones.
  * Native multi-language support: **English (`en`)**, **Spanish (`es`)**, and **Catalan (`ca`)** via `BSKY_LANG`.
  * **User Custom Phrases (`/data/custom_phrases.json`)** with **hot-reloading** (zero downtime, no container restarts).
* 📺 **Intelligent Context Detection:**
  * Accurately distinguishes between a **definitive season finale** and the **latest aired episode** in active weekly broadcasts.
  * **Backlog Rescue:** Special celebration when resuming a TV show after more than 1.5 years (547 days) on hiatus.
  * Open conversation prompts at season conclusions to encourage community engagement.
* 📊 **Periodic Balances & Automated Collages (Pillow):**
  * **Weekly Balance:** Every Monday at 09:30h covering the closed natural week with high-definition **3x3 or 2x2 poster collages**.
  * **Monthly Balance:** On the 1st of every month at 09:30h with consolidated monthly metrics and artwork.
  * **Mid-Month Fun Facts:** On the 15th of every month at 12:00h analyzing binge patterns, peak viewing hours, or longest finished show.
* 🔥 **Streaks and Milestones:** Consecutive daily viewing streak milestones (starting at 7 continuous days) and all-time tally celebrations (e.g., 18,000 episodes, 400 finished TV shows).
* ⚡ **On-Demand Signal Triggers:** Ephemeral trigger files (`trigger_weekly`, `trigger_monthly`, `trigger_fun_fact`) for manual execution from homelab dashboards like **OliveTin**.

---

## 📚 Documentation & Wiki

For in-depth guides, variable references, and configuration walkthroughs:

* ⚙️ **[Configuration & Deployment Guide (`docs/en/CONFIGURATION.md`)](docs/en/CONFIGURATION.md):** Complete `.env` parameters, volume layout, NAS permissions (`PUID`/`PGID`), and modern Compose v2 template.
* ✍️ **[Custom Phrases & Localization Guide (`docs/en/CUSTOM_PHRASES.md`)](docs/en/CUSTOM_PHRASES.md):** Template variables (`{show_title}`, `{season_num}`...), extension mode vs exclusive override mode, and hot-reload mechanism.
* 📊 **[Statistics, Balances & Collages (`docs/en/STATISTICS.md`)](docs/en/STATISTICS.md):** Pillow collage dimensions, calculation logic, and OliveTin dashboard setup.
* 🔌 **[Tracker Providers: SIMKL & WeTrakr (`docs/en/PROVIDERS.md`)](docs/en/PROVIDERS.md):** API key setup, PIN device authorization flows, and automatic token management.

---

## 🚀 Quick Start

### 1. Clone repository and prepare files
```bash
git clone https://github.com/your-username/bsky-media-scrobbler.git
cd bsky-media-scrobbler
cp .env.example .env
mkdir -p data
```

### 2. Configure credentials in `.env`
```env
TRACKER_PROVIDER=simkl
SIMKL_CLIENT_ID=your_simkl_client_id
BSKY_HANDLE=your-account.bsky.social
BSKY_APP_PASSWORD=your_app_password
BSKY_LANG=en
TZ=Europe/Madrid
```

### 3. Start with Docker Compose
```bash
docker compose up -d
```

*(If you omit an initial token in `.env`, run `docker compose logs -f` to view your interactive device authorization PIN).*

---

## 🛠️ Tech Stack

* **Python 3.12**
* [atproto](https://github.com/MarshalX/atproto) - Official AT Protocol SDK for Bluesky.
* [Pillow (PIL)](https://python-pillow.org/) - Graphic composition engine for high-resolution collages.
* [Requests](https://requests.readthedocs.io/) - HTTP client for SIMKL, WeTrakr, and TMDB APIs.

---

## 📄 License

Distributed under the [MIT License](LICENSE).

---

## 🙏 Credits & Acknowledgments

* Originally inspired by [SIMKLTrackerBot](https://github.com/donnyfly/SIMKLTrackerBot) by **@donnyfly**.
* Metadata and tracking services provided by **SIMKL** and **WeTrakr**.
* Artwork and movie metadata powered by **The Movie Database (TMDB)**.
