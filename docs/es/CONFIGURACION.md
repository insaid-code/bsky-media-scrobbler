# ⚙️ Guía de Configuración y Despliegue

Este documento detalla todas las variables de entorno, opciones de personalización y arquitectura de despliegue para **`bsky-media-scrobbler`**.

---

## 📋 Variables de Entorno (`.env`)

| Variable | Tipo | Por Defecto | Descripción |
| :--- | :---: | :---: | :--- |
| `DRY_RUN` | Booleano | `false` | Si se establece en `true`, simula la generación de posts y collages en los logs sin publicar en Bluesky. Ideal para pruebas iniciales. |
| `TRACKER_PROVIDER` | Texto | `wetrakr` | Plataforma de seguimiento activa. Valores admitidos: `wetrakr` o `simkl`. |
| `WETRAKR_CLIENT_ID` | Texto | — | Client ID / API Key de WeTrakr. Requerido si `TRACKER_PROVIDER=wetrakr`. |
| `WETRAKR_CLIENT_SECRET` | Texto | *(opcional)* | Client Secret de WeTrakr. |
| `WETRAKR_ACCESS_TOKEN` | Texto | *(opcional)* | Token de acceso OAuth de WeTrakr. Si se omite, se inicia el flujo interactivo por PIN (`Device Auth`). |
| `SIMKL_CLIENT_ID` | Texto | — | Client ID de la aplicación creada en SIMKL Developers. Requerido si `TRACKER_PROVIDER=simkl`. |
| `SIMKL_USER_TOKEN` | Texto | *(opcional)* | Token de acceso del usuario en SIMKL. Si se omite, el bot iniciará el flujo interactivo de autorización por código PIN (`Device Auth`). |
| `TVDB_API_KEY` | Texto | *(opcional)* | API Key v4 de TheTVDB para traducir automáticamente los nombres de series y películas al castellano (`BSKY_LANG=es`/`ca`) y generar hashtags traducidos. Si se omite, se publican con su nombre original en inglés sin fallos. |
| `BSKY_HANDLE` | Texto | — | Identificador de tu cuenta en Bluesky (ej. `mi-cuenta.bsky.social`). |
| `BSKY_APP_PASSWORD` | Texto | — | Contraseña de aplicación generada en Bluesky (*Ajustes ➜ Privacidad y seguridad ➜ Contraseñas de aplicación*). Nunca uses tu contraseña principal. |
| `BSKY_LANG` | Texto | `es` | Código de idioma para los posts (ej. `es`, `en`, `ca`). Aplica la etiqueta AT-Protocol `langs` y selecciona el archivo base de frases (`locales/es.json`). |
| `POLL_INTERVAL_MINUTES` | Entero | `90` | Frecuencia de sondeo en minutos. Un valor de `90` minutos es el óptimo recomendado para permitir agrupar episodios vistos en sesión continua (maratón). |
| `MAX_POSTS_PER_RUN` | Entero | `6` | Límite máximo de publicaciones a Bluesky por ciclo. Previene ráfagas masivas y bloqueos antispam tras caídas o desconexiones. |
| `POST_DELAY_SECONDS` | Entero | `5` | Pausa de cortesía en segundos entre publicaciones consecutivas dentro de un mismo ciclo. |
| `LINK_DESTINATION` | Texto | `tmdb` | Destino de las tarjetas enriquecidas (`external embeds`). Valores: `tmdb` (The Movie Database), `wetrakr`, `simkl` o `imdb`. |
| `TZ` | Texto | `Europe/Madrid` | Zona horaria del sistema. Esencial para calcular correctamente las franjas horarias de madrugada, mañana, sobremesa, los días de la semana y los cierres de balances. |

---

## 📁 Estructura de Volúmenes y Persistencia

El contenedor requiere dos puntos de montaje esenciales:

```yaml
volumes:
  - ./app:/app       # Código fuente del bot y archivos base de idioma (locales/)
  - ./data:/data     # Datos persistentes del usuario (estado, tokens, frases personalizadas)
```

### Contenido de `/data`
* `state.json`: Base de datos ligera con el registro de última comprobación, hitos celebrados, rachas activas y cola anti-repetición de frases recientes.
* `custom_phrases.json`: *(Opcional)* Archivo donde el usuario añade sus propias frases o reemplaza las predeterminadas sin tocar el código.
* `trigger_monthly`, `trigger_weekly`, `trigger_fun_fact`: Archivos señal efímeros para disparar resúmenes bajo demanda.

---

## 🚀 Despliegue en Docker Compose / Dockge

Crea el archivo `compose.yaml` (utilizando la especificación moderna de Compose v2):

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
      - BSKY_LANG=${BSKY_LANG:-es}
      - POLL_INTERVAL_MINUTES=${POLL_INTERVAL_MINUTES:-90}
      - MAX_POSTS_PER_RUN=${MAX_POSTS_PER_RUN:-6}
      - POST_DELAY_SECONDS=${POST_DELAY_SECONDS:-5}
      - LINK_DESTINATION=${LINK_DESTINATION:-tmdb}
    volumes:
      - ./app:/app
      - ./data:/data
```

> **Nota para usuarios avanzados (Proxy inverso / Dockge):** Si utilizas una red puente compartida (por ejemplo, con Cloudflare Tunnel, Nginx Proxy Manager o Traefik), simplemente agrega tu bloque `networks:` al servicio. Para el 99% de los usuarios, la configuración estándar anterior funciona directamente *out of the box*.

---

## 🔒 Buenas Prácticas de Seguridad
1. **Contraseña de Aplicación Bluesky:** Nunca introduzcas la contraseña maestra de tu cuenta. Genera siempre una contraseña dedicada desde la interfaz web de Bluesky y revócala si cambias de servidor.
2. **Abstracción de Credenciales:** Mantén los tokens y contraseñas estrictamente en tu archivo `.env` o gestor de secretos, asegurando que `.env` esté incluido en `.gitignore`.
