# 🔌 Proveedores de Seguimiento (Trackers)

`bsky-media-scrobbler` soporta de forma nativa e intercambiable dos de las plataformas más potentes de seguimiento multimedia: **WeTrakr** y **SIMKL**.

La elección se realiza mediante la variable de entorno:
```env
TRACKER_PROVIDER=wetrakr    # o 'simkl'
```

---

## 1. WeTrakr (`TRACKER_PROVIDER=wetrakr`)

WeTrakr es un tracker emergente moderno basado en OAuth2 / Device Authorization Grant (RFC 8628), con sincronización avanzada de perfiles, series y biblioteca.

### Obtención de Credenciales
1. Regístrate o accede a tu panel en [WeTrakr](https://wetrakr.com).
2. Crea una aplicación en tus ajustes de desarrollador para obtener tu `WETRAKR_CLIENT_ID` y `WETRAKR_CLIENT_SECRET`.

### Flujo de Autorización Device Flow
WeTrakr utiliza el protocolo RFC 8628 (Device Authorization Flow):
1. Al arrancar con `TRACKER_PROVIDER=wetrakr` sin un token previo, el bot contacta con el endpoint `/oauth/device/code`.
2. Muestra en los logs la URL de activación y el código PIN de usuario:
  ```
  👉 Entra en: https://wetrakr.com/activate
  👉 Introduce el código PIN: WTRK-7890
  ```
3. El contenedor sondea periódicamente hasta confirmar la autorización.
4. En cuanto autorizas la aplicación en tu navegador, el bot almacena `access_token` y `refresh_token` en `data/state.json`.
5. El cliente renueva el token automáticamente antes de su expiración sin requerir intervención del usuario.

---

## 2. SIMKL (`TRACKER_PROVIDER=simkl`)

SIMKL ofrece una API REST madura con seguimiento en tiempo real de episodios de TV, animes y películas.

### Obtención de Credenciales
1. Inicia sesión en [SIMKL](https://simkl.com).
2. Accede a [SIMKL Apps & Developers](https://simkl.com/apps/developer/).
3. Pulsa en **Create new app**.
4. Rellena los datos de tu aplicación y copia tu **Client ID**.

### Modos de Autenticación
* **Modo Directo (Recomendado):** Añade tu `SIMKL_USER_TOKEN` en el archivo `.env`.
* **Modo PIN (Device Flow):** Si dejas `SIMKL_USER_TOKEN` vacío en el `.env`, el bot generará automáticamente un código PIN interactivo visible en los logs de Docker (`docker compose logs -f`):
  ```
  👉 Entra en: https://simkl.com/pin
  👉 Introduce el código PIN: ABCD12
  ```
  Una vez autorizado en la web, el bot guardará el token en `data/state.json` y empezará a sincronizar automáticamente.

---

## 🔄 Paridad de Funcionalidades entre Proveedores

| Funcionalidad | WeTrakr | SIMKL |
| :--- | :---: | :---: |
| Detección de episodios de TV | ✅ | ✅ |
| Agrupación de maratones (`S01E01-E03`) | ✅ | ✅ |
| Detección de películas | ✅ | ✅ |
| Hitos de final de temporada | ✅ | ✅ |
| Rescate de backlog (> 1.5 años) | ✅ | ✅ |
| Generación de collages semanales/mensuales | ✅ | ✅ |
| Contador de rachas (días continuos) | ✅ | ✅ |
| Hitos históricos de episodios y series | ✅ | ✅ |
