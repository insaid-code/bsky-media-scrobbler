# ⚙️ Guia de Configuració i Desplegament

Aquest document detalla totes les variables d'entorn, opcions de personalització i l'arquitectura de desplegament per a **`bsky-media-scrobbler`**.

---

## 📋 Variables d'Entorn (`.env`)

| Variable | Tipus | Per Defecte | Descripció |
| :--- | :---: | :---: | :--- |
| `DRY_RUN` | Booleà | `false` | Si s'estableix en `true`, simula la generació de publicacions i collages als registres sense publicar a Bluesky. Ideal per a proves inicials. |
| `TRACKER_PROVIDER` | Text | `wetrakr` | Plataforma de seguiment activa. Valors admesos: `wetrakr` o `simkl`. |
| `WETRAKR_CLIENT_ID` | Text | — | Client ID / API Key de WeTrakr. Requerit si `TRACKER_PROVIDER=wetrakr`. |
| `WETRAKR_CLIENT_SECRET` | Text | *(opcional)* | Client Secret de WeTrakr. |
| `WETRAKR_ACCESS_TOKEN` | Text | *(opcional)* | Token d'accés OAuth de WeTrakr. Si s'omet, s'inicia el flux interactiu per codi PIN (`Device Auth`). |
| `SIMKL_CLIENT_ID` | Text | — | Client ID de l'aplicació creada a SIMKL Developers. Requerit si `TRACKER_PROVIDER=simkl`. |
| `SIMKL_USER_TOKEN` | Text | *(opcional)* | Token d'accés de l'usuari a SIMKL. Si s'omet, el bot iniciarà el flux interactiu d'autorització per codi PIN (`Device Auth`). |
| `TVDB_API_KEY` | Text | *(opcional)* | Clau d'API v4 de TheTVDB per traduir automàticament els noms de sèries i pel·lícules al castellà (`BSKY_LANG=ca`/`es`) i generar hashtags traduïts. Si s'omet, es publiquen amb el nom original en anglès sense fallades. |
| `BSKY_HANDLE` | Text | — | Identificador del teu compte a Bluesky (ex. `el-teu-compte.bsky.social`). |
| `BSKY_APP_PASSWORD` | Text | — | Contrasenya d'aplicació generada a Bluesky (*Ajustos ➜ Privadesa i seguretat ➜ Contrasenyes d'aplicació*). No facis servir mai la teva contrasenya principal. |
| `BSKY_LANG` | Text | `ca` | Codi d'idioma per a les publicacions (ex. `ca`, `es`, `en`). Aplica l'etiqueta AT-Protocol `langs` i selecciona el fitxer base de frases (`locales/ca.json`). |
| `POLL_INTERVAL_MINUTES` | Enter | `90` | Freqüència de sondeig en minuts. Un valor de `90` minuts és l'òptim recomanat per permetre agrupar capítols vistos en sessió contínua (marató). |
| `MAX_POSTS_PER_RUN` | Enter | `6` | Límit màxim de publicacions a Bluesky per cicle. Prevé ràfegues massives i bloquejos antispam després de caigudes o desconnexions. |
| `POST_DELAY_SECONDS` | Enter | `5` | Pausa de cortesia en segons entre publicacions consecutives dins d'un mateix cicle. |
| `LINK_DESTINATION` | Text | `tmdb` | Destinació de les targetes enriquides (`external embeds`). Valors: `tmdb` (The Movie Database), `wetrakr`, `simkl` o `imdb`. |
| `TZ` | Text | `Europe/Madrid` | Zona horària del sistema. Essencial per calcular correctament les franges horàries de matinada, matí, sobretaula, els dies de la setmana i els tancaments de balanços. |

---

## 📁 Estructura de Volums i Persistència

El contenidor requereix dos punts de muntatge essencials:

```yaml
volumes:
  - ./app:/app       # Codi font del bot i fitxers base d'idioma (locales/)
  - ./data:/data     # Dades persistents de l'usuari (estat, tokens, frases personalitzades)
```

### Contingut de `/data`
* `state.json`: Base de dades lleugera amb el registre de l'última comprovació, fites celebrades, ratxes actives i cua anti-repetició de frases recents.
* `custom_phrases.json`: *(Opcional)* Fitxer on l'usuari afegeix les seves pròpies frases o reemplaça les predeterminades sense tocar el codi.
* `trigger_monthly`, `trigger_weekly`, `trigger_fun_fact`: Fitxers senyal efímers per disparar resums a demanda.

---

## 🚀 Desplegament a Docker Compose / Dockge

Crea el fitxer `compose.yaml` (utilitzant l'especificació moderna de Compose v2):

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
      - TVDB_API_KEY=${TVDB_API_KEY:-}
      - WETRAKR_CLIENT_ID=${WETRAKR_CLIENT_ID}
      - WETRAKR_CLIENT_SECRET=${WETRAKR_CLIENT_SECRET}
      - BSKY_HANDLE=${BSKY_HANDLE}
      - BSKY_APP_PASSWORD=${BSKY_APP_PASSWORD}
      - BSKY_LANG=${BSKY_LANG:-ca}
      - POLL_INTERVAL_MINUTES=${POLL_INTERVAL_MINUTES:-90}
      - MAX_POSTS_PER_RUN=${MAX_POSTS_PER_RUN:-6}
      - POST_DELAY_SECONDS=${POST_DELAY_SECONDS:-5}
      - LINK_DESTINATION=${LINK_DESTINATION:-tmdb}
    volumes:
      - ./app:/app
      - ./data:/data
```

> **Nota per a usuaris avançats (Reverse Proxy / Dockge):** Si fas servir una xarxa pont compartida (per exemple, amb Cloudflare Tunnel, Nginx Proxy Manager o Traefik), simplement afegeix el teu bloc `networks:` al servei. Per al 99% dels usuaris, la configuració estàndard anterior funciona directament *out of the box*.

---

## 🔒 Bones Pràctiques de Seguretat
1. **Contrasenya d'Aplicació Bluesky:** No introdueixis mai la contrasenya mestra del teu compte. Genera sempre una contrasenya dedicada des de la interfície web de Bluesky i revoca-la si canvies de servidor.
2. **Abstracció de Credencials:** Mantén els tokens i contrasenyes estrictament al teu fitxer `.env` o gestor de secrets, assegurant-te que `.env` estigui inclòs a `.gitignore`.
