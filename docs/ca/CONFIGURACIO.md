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
| `BSKY_HANDLE` | Text | — | Identificador del teu compte a Bluesky (ex. `el-teu-compte.bsky.social`). |
| `BSKY_APP_PASSWORD` | Text | — | Contrasenya d'aplicació generada a Bluesky (*Ajustos ➜ Privadesa i seguretat ➜ Contrasenyes d'aplicació*). No facis servir mai la teva contrasenya principal. |
| `BSKY_LANG` | Text | `es` | Codi d'idioma per a les publicacions (ex. `ca`, `es`, `en`). Aplica l'etiqueta AT-Protocol `langs` i selecciona el fitxer base de frases (`locales/ca.json`). |
| `POLL_INTERVAL_MINUTES` | Enter | `90` | Freqüència de sondeig en minuts. Un valor de `90` minuts és l'òptim recomanat per permetre agrupar capítols vistos en sessió contínua (marató). |
| `LINK_DESTINATION` | Text | `tmdb` | Destinació de les targetes enriquides (`external embeds`). Valors: `tmdb` (The Movie Database), `wetrakr`, `simkl` o `imdb`. |
| `TZ` | Text | `Europe/Madrid` | Zona horària del sistema. Essencial per calcular correctament les franges horàries de matinada, matí, sobretaula, els dies de la setmana i els tancaments de balanços. |
| `PUID` / `PGID` | Enter | `1026` / `100` | Identificadors d'usuari i grup per a la gestió de permisos en volums persistents en sistemes NAS (Synology, Unraid, TrueNAS). |

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

Crea el fitxer `compose.yaml` (utilitzant l'especificació moderna sense l'atribut obsolet `version`):

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
      - BSKY_LANG=${BSKY_LANG:-ca}
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

---

## 🔒 Bones Pràctiques de Seguretat
1. **Contrasenya d'Aplicació Bluesky:** No introdueixis mai la contrasenya mestra del teu compte. Genera sempre una contrasenya dedicada des de la interfície web de Bluesky i revoca-la si canvies de servidor.
2. **Abstracció de Credencials:** Mantén els tokens i contrasenyes estrictament al teu fitxer `.env` o gestor de secrets, assegurant-te que `.env` estigui inclòs a `.gitignore`.
