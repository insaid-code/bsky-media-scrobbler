# 🔌 Supported Trackers: WeTrakr and SIMKL

`bsky-media-scrobbler` seamlessly integrates with two leading media tracking platforms: **WeTrakr** and **SIMKL**.

Switch between providers via your environment file:
```env
TRACKER_PROVIDER=wetrakr    # or 'simkl'
```

---

## 1. WeTrakr (`TRACKER_PROVIDER=wetrakr`)

WeTrakr is a modern, privacy-focused media tracker using OAuth2 / Device Authorization Grant (RFC 8628).

### Getting Credentials
1. Register or sign in to [WeTrakr](https://wetrakr.com).
2. Create an application in your developer settings to get your `WETRAKR_CLIENT_ID` and `WETRAKR_CLIENT_SECRET`.

### Device Authorization Flow
1. When starting with `TRACKER_PROVIDER=wetrakr` without a stored token, the scrobbler requests a device code.
2. Check your Docker logs for the activation prompt:
  ```
  👉 Visit: https://wetrakr.com/activate
  👉 Enter PIN: WTRK-7890
  ```
3. Authorize the application in your browser.
4. The scrobbler automatically polls, receives the `access_token` and `refresh_token`, and stores them securely in `data/state.json`.
5. Tokens are refreshed automatically before expiration with zero manual intervention.

---

## 2. SIMKL (`TRACKER_PROVIDER=simkl`)

SIMKL offers a mature REST API for tracking TV episodes, anime, and movies.

### Getting Credentials
1. Sign in to [SIMKL](https://simkl.com).
2. Visit [SIMKL Apps & Developers](https://simkl.com/apps/developer/).
3. Click **Create new app**.
4. Fill in your application details and copy your **Client ID**.

### Authentication Modes
* **Direct Token Mode (Recommended):** Place your `SIMKL_USER_TOKEN` in `.env`.
* **PIN Device Flow:** If `SIMKL_USER_TOKEN` is left empty in `.env`, the bot will automatically generate an interactive PIN code in Docker logs (`docker compose logs -f`):
  ```
  👉 Visit: https://simkl.com/pin
  👉 Enter PIN: ABCD12
  ```
  Once approved, the token is saved to `data/state.json` and sync starts immediately.

---

## 🔄 Feature Parity Matrix

| Feature | WeTrakr | SIMKL |
| :--- | :---: | :---: |
| TV episode scrobbling | ✅ | ✅ |
| Binge grouping (`S01E01-E03`) | ✅ | ✅ |
| Movie watch scrobbling | ✅ | ✅ |
| Season finale detection | ✅ | ✅ |
| Backlog rescue detection (> 1.5 years) | ✅ | ✅ |
| Weekly/monthly poster collages | ✅ | ✅ |
| Daily streak counter | ✅ | ✅ |
| All-time milestone celebrations | ✅ | ✅ |
