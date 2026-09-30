# 🔌 Proveïdors de Seguiment (Trackers)

`bsky-media-scrobbler` suporta de forma nativa i intercanviable dues de les plataformes més potents de seguiment multimèdia: **WeTrakr** i **SIMKL**.

L'elecció es realitza mitjançant la variable d'entorn:
```env
TRACKER_PROVIDER=wetrakr    # o 'simkl'
```

---

## 1. WeTrakr (`TRACKER_PROVIDER=wetrakr`)

WeTrakr és un tracker emergent modern basat en OAuth2 / Device Authorization Grant (RFC 8628), amb sincronització avançada de perfils, sèries i biblioteca.

### Obtenció de Credencials
1. Registra't o accedeix al teu tauler a [WeTrakr](https://wetrakr.com).
2. Crea una aplicació als teus paràmetres de desenvolupador per obtenir el teu `WETRAKR_CLIENT_ID` i `WETRAKR_CLIENT_SECRET`.

### Flux d'Autorització Device Flow
WeTrakr utilitza el protocol RFC 8628 (Device Authorization Flow):
1. En arrencar amb `TRACKER_PROVIDER=wetrakr` sense un token previ, el bot contacta amb l'extrem `/oauth/device/code`.
2. Mostra als registres (logs) l'URL d'activació i el codi PIN d'usuari:
  ```
  👉 Entra a: https://wetrakr.com/activate
  👉 Introdueix el codi PIN: WTRK-7890
  ```
3. El contenidor sondeja periòdicament fins a confirmar l'autorització.
4. Tan bon punt autoritzes l'aplicació al teu navegador, el bot emmagatzema `access_token` i `refresh_token` a `data/state.json`.
5. El client renova el token automàticament abans de la seva expiració sense requerir intervenció de l'usuari.

---

## 2. SIMKL (`TRACKER_PROVIDER=simkl`)

SIMKL ofereix una API REST madura amb seguiment en temps real d'episodis de TV, animes i pel·lícules.

### Obtenció de Credencials
1. Inicia sessió a [SIMKL](https://simkl.com).
2. Accedeix a [SIMKL Apps & Developers](https://simkl.com/apps/developer/).
3. Fes clic a **Create new app**.
4. Emplena les dades de la teva aplicació i copia el teu **Client ID**.

### Modes d'Autenticació
* **Mode Directe (Recomanat):** Afegeix el teu `SIMKL_USER_TOKEN` al fitxer `.env`.
* **Mode PIN (Device Flow):** Si deixes `SIMKL_USER_TOKEN` buit al `.env`, el bot generarà automàticament un codi PIN interactiu visible als registres de Docker (`docker compose logs -f`):
  ```
  👉 Entra a: https://simkl.com/pin
  👉 Introdueix el codi PIN: ABCD12
  ```
  Un cop autoritzat al web, el bot desarà el token a `data/state.json` i començarà a sincronitzar automàticament.

---

## 🔄 Paritat de Funcionalitats entre Proveïdors

| Funcionalitat | WeTrakr | SIMKL |
| :--- | :---: | :---: |
| Detecció d'episodis de TV | ✅ | ✅ |
| Agrupació de maratons (`S01E01-E03`) | ✅ | ✅ |
| Detecció de pel·lícules | ✅ | ✅ |
| Fites de final de temporada | ✅ | ✅ |
| Rescat de backlog (> 1.5 anys) | ✅ | ✅ |
| Generació de collages setmanals/mensuals | ✅ | ✅ |
| Comptador de ratxes (dies continus) | ✅ | ✅ |
| Fites històriques d'episodis i sèries | ✅ | ✅ |
