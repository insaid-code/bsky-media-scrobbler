# 📺 Bluesky Media Scrobbler (`bsky-media-scrobbler`)

<p align="center">
  <b>Idioma:</b>
  <a href="README.md">🇬🇧 English</a> •
  <a href="README.es.md">🇪🇸 Español</a> •
  <a href="README.ca.md">🏴󠁥󠁳󠁣󠁴󠁿 Català</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue.svg?logo=python" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker" alt="Docker Ready" />
  <img src="https://img.shields.io/badge/Bluesky-AT%20Protocol-0085ff.svg?logo=bluesky" alt="Bluesky" />
  <img src="https://img.shields.io/badge/Licencia-MIT-green.svg" alt="Licencia MIT" />
</p>

Bot autónomo en Python para Docker que monitoriza tu actividad en tus plataformas de seguimiento favoritas (**WeTrakr**, **SIMKL**) y la publica de forma enriquecida en **Bluesky** con tarjetas externas hacia **TMDB**, collages visuales en alta definición, balances periódicos y contador de rachas.

---

## ✨ Características Principales

* 🔌 **Multi-Tracker Universal:** Soporte nativo para **WeTrakr** y **SIMKL** seleccionable mediante variable de entorno (`TRACKER_PROVIDER`).
* 📦 **Agrupación Inteligente de Maratones:** Si ves varios capítulos consecutivos (ej. `T01E01–E03`), los agrupa en un único post limpio para no saturar tu timeline.
* 🎬 **Fichas Enriquecidas (TMDB):** Tarjetas interactivas externas hacia The Movie Database con carátula oficial en alta definición.
* ✍️ **Motor de Frases y Multi-idioma (i18n):**
  * Más de 220 frases oficiales clasificadas por franjas horarias, días de la semana, volumen de sesión, finales de temporada e hitos de trama.
  * Soporte nativo multilingüe: **Español (`es`)**, **Inglés (`en`)** y **Catalán (`ca`)** mediante `BSKY_LANG`.
  * **Frases personalizadas (`/data/custom_phrases.json`)** con **recarga en caliente (hot-reload)** sin necesidad de reiniciar el contenedor.
* 📺 **Detección Contextual Avanzada:**
  * Distingue con precisión entre un **final definitivo de temporada** y el **último emitido** en series en emisión semanal.
  * Detección de **rescate de backlog** tras más de año y medio sin actividad en una serie.
  * Llamadas a la conversación y preguntas abiertas para fomentar la interacción en Bluesky.
* 📊 **Informes y Collages Periódicos con Pillow:**
  * **Balance Semanal:** Los lunes a las 09:30h con la semana natural cerrada y **collage de carátulas (3x3 o 2x2)** en alta definición.
  * **Balance Mensual:** El día 1 de cada mes a las 09:30h con el balance cerrado del mes anterior.
  * **Curiosidades (Fun Facts):** El día 15 de cada mes a las 12:00h analizando patrones de maratón, hora punta o la serie más larga completada.
* 🔥 **Rachas e Hitos:** Celebración de rachas consecutivas (a partir de 7 días continuos) e hitos históricos de episodios, series completadas y películas.
* ⚡ **Disparadores Manuales bajo Demanda:** Archivos señal (`trigger_weekly`, `trigger_monthly`, `trigger_fun_fact`) para forzar reportes desde paneles como **OliveTin**.

---

## 📚 Documentación Completa y Wiki

Para consultar guías detalladas paso a paso sobre cada módulo del proyecto:

* ⚙️ **[Guía de Configuración y Variables de Entorno (`docs/es/CONFIGURACION.md`)](docs/es/CONFIGURACION.md):** Parámetros del `.env`, estructura de volúmenes, permisos y plantilla para Dockge/Compose.
* ✍️ **[Motor de Frases Personalizadas y Multi-idioma (`docs/es/FRASES_PERSONALIZADAS.md`)](docs/es/FRASES_PERSONALIZADAS.md):** Cómo crear tu propio `custom_phrases.json`, variables disponibles (`{show_title}`, `{season_num}`...), modos suma vs reemplazo y recarga en caliente.
* 📊 **[Estadísticas, Informes y Collages Visuales (`docs/es/ESTADISTICAS.md`)](docs/es/ESTADISTICAS.md):** Calendario de balances, especificaciones de imagen de Pillow y configuración en OliveTin.
* 🔌 **[Proveedores de Seguimiento: WeTrakr y SIMKL (`docs/es/PROVEEDORES.md`)](docs/es/PROVEEDORES.md):** Obtención de API keys, flujo de autorización por código PIN (`Device Auth`) y renovación automática de tokens.
* 🗺️ **[Roadmap del Proyecto (`ROADMAP.md`)](ROADMAP.md):** Funcionalidades planificadas, control de bugs latentes y prioridades de versión.

---

## 🚀 Despliegue Rápido (Quick Start)

### 1. Clonar y preparar entorno
```bash
git clone https://github.com/tu-usuario/bsky-media-scrobbler.git
cd bsky-media-scrobbler
cp .env.example .env
mkdir -p data
```

### 2. Configurar credenciales en `.env`
```env
TRACKER_PROVIDER=wetrakr
WETRAKR_CLIENT_ID=tu_wetrakr_client_id
WETRAKR_CLIENT_SECRET=tu_wetrakr_client_secret
BSKY_HANDLE=tu_cuenta.bsky.social
BSKY_APP_PASSWORD=tu_app_password_aqui
BSKY_LANG=es
TZ=Europe/Madrid
```

### 3. Iniciar el servicio con Docker Compose
```bash
docker compose up -d
```

*(Si no especificas un token inicial en `.env`, consulta `docker compose logs -f` para ver el código PIN interactivo y autorizar tu cuenta con un toque).*

---

## 🛠️ Tecnologías y Dependencias

* **Python 3.12**
* [atproto](https://github.com/MarshalX/atproto) - SDK oficial para el protocolo AT de Bluesky.
* [Pillow (PIL)](https://python-pillow.org/) - Motor de composición gráfica de collages en alta definición.
* [Requests](https://requests.readthedocs.io/) - Cliente HTTP para consumo de APIs de WeTrakr, SIMKL y TMDB.

---

## 📄 Licencia

Este proyecto se distribuye bajo la licencia [MIT](LICENSE).

---

## 🙏 Créditos y Agradecimientos

* Inspirado originalmente en el proyecto [SIMKLTrackerBot](https://github.com/donnyfly/SIMKLTrackerBot) de **@donnyfly**.
* A las plataformas **WeTrakr** y **SIMKL** por sus APIs y servicios de seguimiento.
* A **The Movie Database (TMDB)** por sus metadatos y carátulas en alta definición.
