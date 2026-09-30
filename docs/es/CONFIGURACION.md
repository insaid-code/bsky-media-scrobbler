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
| `BSKY_HANDLE` | Texto | — | Identificador de tu cuenta en Bluesky (ej. `mi-cuenta.bsky.social`). |
| `BSKY_APP_PASSWORD` | Texto | — | Contraseña de aplicación generada en Bluesky (*Ajustes ➜ Privacidad y seguridad ➜ Contraseñas de aplicación*). Nunca uses tu contraseña principal. |
| `BSKY_LANG` | Texto | `es` | Código de idioma para los posts (ej. `es`, `en`). Aplica la etiqueta AT-Protocol `langs` y selecciona el archivo base de frases (`locales/es.json`). |
| `POLL_INTERVAL_MINUTES` | Entero | `90` | Frecuencia de sondeo en minutos. Un valor de `90` minutos es el óptimo recomendado para permitir agrupar episodios vistos en sesión continua (maratón). |
| `LINK_DESTINATION` | Texto | `tmdb` | Destino de las tarjetas enriquecidas (`external embeds`). Valores: `tmdb` (The Movie Database), `wetrakr`, `simkl` o `imdb`. |
| `TZ` | Texto | `Europe/Madrid` | Zona horaria del sistema. Esencial para calcular correctamente las franjas horarias de madrugada, mañana, sobremesa, los días de la semana y los cierres de balances. |
| `PUID` / `PGID` | Entero | `1026` / `100` | Identificadores de usuario y grupo para la gestión de permisos en volúmenes persistentes en sistemas NAS (Synology, Unraid, TrueNAS). |

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

Crea el archivo `compose.yaml` (utilizando la especificación moderna sin atributo obsoleto `version`):

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
      - BSKY_LANG=${BSKY_LANG:-es}
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

## 🔒 Buenas Prácticas de Seguridad
1. **Contraseña de Aplicación Bluesky:** Nunca introduzcas la contraseña maestra de tu cuenta. Genera siempre una contraseña dedicada desde la interfaz web de Bluesky y revócala si cambias de servidor.
2. **Abstracción de Credenciales:** Mantén los tokens y contraseñas estrictamente en tu archivo `.env` o gestor de secretos, asegurando que `.env` esté incluido en `.gitignore`.
