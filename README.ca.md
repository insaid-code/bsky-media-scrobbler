# 📺 Bluesky Media Scrobbler (`bsky-media-scrobbler`)

<p align="center">
  <b>Llengua:</b>
  <a href="README.md">🇬🇧 English</a> •
  <a href="README.es.md">🇪🇸 Español</a> •
  <a href="README.ca.md">🏴󠁥󠁳󠁣󠁴󠁿 Català</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue.svg?logo=python" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker" alt="Docker Ready" />
  <img src="https://img.shields.io/badge/Bluesky-AT%20Protocol-0085ff.svg?logo=bluesky" alt="Bluesky" />
  <img src="https://img.shields.io/badge/Llicència-MIT-green.svg" alt="Llicència MIT" />
  <a href="https://ko-fi.com/insaid"><img src="https://img.shields.io/badge/Ko--fi-Donar-F16061?logo=ko-fi&logoColor=white" alt="Ko-fi" /></a>
</p>

Bot autònom en Python per a Docker que monitoritza la teva activitat a les teves plataformes de seguiment preferides (**WeTrakr**, **SIMKL**) i la publica de forma enriquida a **Bluesky** amb targetes externes cap a **TMDB**, collages visuals en alta definició, balanços periòdics i comptador de ratxes.

---

## ✨ Característiques Principals

* 🔌 **Multi-Tracker Universal:** Suport natiu per a **WeTrakr** i **SIMKL** seleccionable mitjançant variable d'entorn (`TRACKER_PROVIDER`).
* 📦 **Agrupació Intel·ligent de Maratons:** Si mires diversos capítols consecutius (ex. `T01E01–E03`), els agrupa en un únic post net per no saturar el teu timeline.
* 🎬 **Fitxes Enriquides (TMDB):** Targetes interactives externes cap a The Movie Database amb caràtula oficial en alta definició.
* ✍️ **Motor de Frases i Multi-idioma (i18n):**
  * Més de 220 frases oficials classificades per franges horàries, dies de la setmana, volum de sessió, finals de temporada i fites de trama.
  * Suport natiu multilingüe: **Català (`ca`)**, **Espanyol (`es`)** i **Anglès (`en`)** mitjançant `BSKY_LANG`.
  * **Frases personalitzades (`/data/custom_phrases.json`)** amb **recàrrega en calent (hot-reload)** sense necessitat de reiniciar el contenidor.
* 📺 **Detecció Contextual Avançada:**
  * Distingeix amb precisió entre un **final definitiu de temporada** i l'**últim emès** en sèries en emissió setmanal activa.
  * Detecció de **rescat de backlog** després de més d'any i mig sense activitat en una sèrie.
  * Crides a la conversa i preguntes obertes per fomentar la interacció a Bluesky.
* 📊 **Informes i Collages Periòdics amb Pillow:**
  * **Balanç Setmanal:** Els dilluns a les 09:30h amb la setmana natural tancada i **collage de caràtules (3x3 o 2x2)** en alta definició.
  * **Balanç Mensual:** El dia 1 de cada mes a les 09:30h amb el balanç tancat del mes anterior.
  * **Curiositats (Fun Facts):** El dia 15 de cada mes a les 12:00h analitzant patrons de marató, hora punta o la sèrie més llarga completada.
* 🔥 **Ratxes i Fites:** Celebració de ratxes consecutives (a partir de 7 dies continus) i fites històriques d'episodis, sèries completades i pel·lícules.
* ⚡ **Disparadors Manuals a Demanda:** Fitxers senyal (`trigger_weekly`, `trigger_monthly`, `trigger_fun_fact`) per forçar informes des de panells com **OliveTin**.

---

## 📚 Documentació i Wiki

Per consultar guies detallades pas a pas sobre cada mòdul del projecte:

* ⚙️ **[Guia de Configuració i Variables d'Entorn (`docs/ca/CONFIGURACIO.md`)](docs/ca/CONFIGURACIO.md):** Paràmetres del `.env`, estructura de volums, permisos i plantilla per a Dockge/Compose.
* ✍️ **[Motor de Frases Personalitzades (`docs/ca/FRASES_PERSONALITZADES.md`)](docs/ca/FRASES_PERSONALITZADES.md):** Com crear el teu propi `custom_phrases.json`, variables disponibles (`{show_title}`, `{season_num}`...), modes suma vs reemplaçament i recàrrega en calent.
* 📊 **[Estadístiques, Informes i Collages Visuals (`docs/ca/ESTADISTIQUES.md`)](docs/ca/ESTADISTIQUES.md):** Calendari de balanços, especificacions d'imatge de Pillow i configuració a OliveTin.
* 🔌 **[Proveïdors de Seguiment: WeTrakr i SIMKL (`docs/ca/PROVEIDORS.md`)](docs/ca/PROVEIDORS.md):** Obtenció d'API keys, flux d'autorització per codi PIN (`Device Auth`) i renovació automàtica de tokens.
* 🗺️ **[Full de Ruta del Projecte (`ROADMAP.md`)](ROADMAP.md):** Funcionalitats planificades, control d'errors latents i prioritats de versió.

---

## 🚀 Desplegament Ràpid (Quick Start)

### 1. Clonar i preparar entorn
```bash
git clone https://github.com/el-teu-usuari/bsky-media-scrobbler.git
cd bsky-media-scrobbler
cp .env.example .env
mkdir -p data
```

### 2. Configurar credencials a `.env`
```env
TRACKER_PROVIDER=wetrakr
WETRAKR_CLIENT_ID=el_teu_wetrakr_client_id
WETRAKR_CLIENT_SECRET=el_teu_wetrakr_client_secret
BSKY_HANDLE=el-teu-compte.bsky.social
BSKY_APP_PASSWORD=la_teva_app_password
BSKY_LANG=ca
TZ=Europe/Madrid
```

### 3. Iniciar el servei amb Docker Compose
```bash
docker compose up -d
```

---

## 🛠️ Tecnologies i Dependències

* **Python 3.12**
* [atproto](https://github.com/MarshalX/atproto) - SDK oficial per al protocol AT de Bluesky.
* [Pillow (PIL)](https://python-pillow.org/) - Motor de composició gràfica de collages en alta definició.
* [Requests](https://requests.readthedocs.io/) - Client HTTP per al consum d'APIs de WeTrakr, SIMKL i TMDB.

---

## ☕ Dona suport al Projecte

Si `bsky-media-scrobbler` et resulta útil, dóna vida al teu mur de Bluesky o t'estalvia temps agrupant les teves maratons, considera convidar-me a un cafè! Qualsevol suport és immensament agraït i ajuda a mantenir el projecte actiu.

<p align="center">
  <a href="https://ko-fi.com/insaid">
    <img src="https://storage.ko-fi.com/cdn/kofi3.png?v=3" height="38" alt="Convida'm a un cafè a ko-fi.com" />
  </a>
</p>

---

## 📄 Llicència

Aquest projecte es distribueix sota la llicència [MIT](LICENSE).

---

## 🙏 Crèdits i Agraïments

* Inspirat originalment en el projecte [SIMKLTrackerBot](https://github.com/donnyfly/SIMKLTrackerBot) de **@donnyfly**.
* A les plataformes **WeTrakr** i **SIMKL** per les seves APIs i serveis de seguiment.
* A **The Movie Database (TMDB)** per les seves metadades i caràtules en alta definició.
