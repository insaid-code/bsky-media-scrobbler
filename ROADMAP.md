# 🗺️ Roadmap — bsky-media-scrobbler

> Documento de planificación y seguimiento de mejoras. Última actualización: **1 de octubre de 2026**.  
> Estado actual: **v1.0.0** — SIMKL + WeTrakr operativos, collages Pillow, i18n (ES/CA/EN), Docker Compose, triggers manuales.

---

## 🚦 Leyenda de estado

| Icono | Estado |
|:------|:-------|
| 🔴 | Bugs / Puntos ciegos — Riesgo real en producción |
| 🟡 | Planificado — En scope para próxima versión |
| 🟢 | Implementado ✅ |
| ⬜ | Descartado — No aplica a este proyecto |

---

## 🚨 Puntos Ciegos — Bugs Latentes

> Estos no son features sino riesgos reales que hay que corregir antes de hacer el proyecto público o en cuanto aparezcan en producción.

### PC-01 🔴 — "At-least-once delivery": riesgo de doble post tras crash
**Probabilidad:** Baja · **Impacto:** Alto

El flujo actual es: publicar en Bluesky → guardar en `state.json`. Si el proceso muere entre esos dos pasos (OOM, reinicio del NAS, corte de luz), al arrancar el episodio se vuelve a publicar.

**Solución prevista:**  
Guardar el estado *antes* de publicar usando un campo `"pending_announcement"` en `state.json`. Si el post falla, el campo queda pendiente y se reintenta limpiamente en el siguiente ciclo.

---

### PC-02 🔴 — Sin rate limiting: backlog flood en Bluesky
**Probabilidad:** Media · **Impacto:** Medio

Tras una caída del NAS o un periodo sin conexión, el bot publicaría decenas de posts en minutos. Riesgo de ser marcado como spam y de saturar a los seguidores.

**Solución prevista:**  
Variable `MAX_POSTS_PER_HOUR` (default: `10`) en el `.env`. Cola de posts que se vacía gradualmente respetando el límite. Forma parte de la v1.1.

---

### PC-03 🟡 — Anime/shows con doble categoría en SIMKL
**Probabilidad:** Baja · **Impacto:** Medio

Algunas series están categorizadas en SIMKL bajo `shows` Y `anime` simultáneamente. El bot las procesa dos veces y podría anunciar el mismo episodio con claves distintas (`anime:ID:S:E` ≠ `shows:ID:S:E`).

**Solución prevista:**  
Deduplicar por `simkl_id` antes de procesar, ignorando el `media_type` como parte de la clave de deduplicación.

---

### PC-04 🟡 — Fun fact: rotación por `month % 3` es determinista, no aleatoria
**Probabilidad:** Cierta · **Impacto:** Bajo

Octubre siempre mostrará el Tema 1, Noviembre el Tema 2... para siempre. El mismo seguidor verá el mismo tipo de curiosidad cada año.

**Solución prevista:**  
Guardar en `state.json` cuántas veces se ha publicado cada tema y rotar al menos usado. Ya existe la infraestructura de `last_stats_posted`.

---

### PC-05 🟡 — Sin alerta si el token de autenticación expira definitivamente
**Probabilidad:** Baja · **Impacto:** Alto

Si SIMKL o WeTrakr invalidan el refresh_token (cambio de contraseña, revocación), el bot deja de publicar en silencio. No hay ningún aviso externo.

**Solución prevista:**  
Cuando la renovación del token falla después de N reintentos, enviar notificación vía Pushover antes de detener el contenedor.

---

## 🟡 v1.1 — Features Planificadas

### F-01 🟡 — Resumen Anual con Collage 3×3
**Prioridad: Alta** · Esfuerzo estimado: Medio

Post automático el **1 de enero** (o trigger manual) con el balance del año completo:
- Episodios totales, películas, tiempo en pantalla
- Top show del año y top película
- Collage 3×3 con las 9 carátulas más vistas del año
- Milestones anuales (series completadas, récord de racha, etc.)

La infraestructura ya existe (`check_monthly` es el modelo); solo requiere ampliar el rango temporal a 12 meses y añadir el marcador `"yearly"` en `last_stats_posted`.

---

### F-02 🟡 — Rate Limiter de Posts
**Prioridad: Alta** · Esfuerzo estimado: Bajo

Variable de entorno `MAX_POSTS_PER_HOUR` (default: `10`).  
En presencia de backlog, los posts se espacian automáticamente respetando el límite. Los posts de estadísticas (semanales, mensuales) tienen prioridad y nunca se retienen.

---

### F-03 🟡 — Post de Valoración Explícita (Rating Post)
**Prioridad: Media** · Esfuerzo estimado: Medio

**¿Cómo funciona?**  
Si en SIMKL/WeTrakr puntúas una película o serie *después* de haberla visto (el post de scrobble ya fue publicado y olvidado), en el siguiente ciclo de comprobación el bot detecta que un ítem ya anunciado tiene un `user_rating` nuevo o modificado y genera un post independiente:

```
⭐ Nota tardía: Le doy un 9/10 a Breaking Bad T4.
Una de las mejores temporadas que recuerdo. El arco
de Gus Fring es perfecto.

#Series #BreakingBad #Simkl
```

El rating del post de scrobble normal (si ya tenías nota en el momento de verlo) no cambia. Este mecanismo actúa solo cuando la nota aparece o cambia *después* del anuncio.

**Implementación:**  
Nuevo campo `"ratings"` en `state.json` con `{ "simkl_id": rating }`. En cada ciclo se compara el rating actual del ítem con el almacenado. Si hay cambio y el ítem ya fue anunciado, se genera el post de valoración.

---

## 🟢 v1.2 — Features en Backlog

### F-04 🟡 — Fun Fact: Cementerio de Series Dropped
**Prioridad: Media** · Esfuerzo estimado: Bajo

Nueva curiosidad de datos para el día 15 del mes (Tema 3 del ciclo de fun facts):

```
💀 El cementerio seriófiio

De las X series que empecé, Y las dejé a medias.
🏆 La que más aguanté antes de tirar la toalla:
   Dark (S03E04 — 28 episodios)
⚡ La más fugaz: The Acolyte (2 episodios)

¿Cuál es tu serie más arrepentida? 📺
```

WeTrakr ya tiene el endpoint `/sync/tracking/dropped/shows` implementado y funcional. Para SIMKL habría que filtrar los ítems con `status = "notinteresting"` / `"dropped"`.

---

### F-05 🟡 — Multi-cuenta Bluesky
**Prioridad: Baja** · Esfuerzo estimado: Alto

Permitir N perfiles Bluesky publicando desde un mismo contenedor, cada uno con su propio idioma y tracker:

```yaml
# compose.yaml hipotético
- BSKY_ACCOUNT_1_HANDLE=@devorando-series.bsky.social
- BSKY_ACCOUNT_1_LANG=es
- BSKY_ACCOUNT_1_TRACKER=simkl
- BSKY_ACCOUNT_2_HANDLE=@media-scrobbler.bsky.social  
- BSKY_ACCOUNT_2_LANG=en
- BSKY_ACCOUNT_2_TRACKER=wetrakr
```

**Actualmente** esto ya funciona arrancando dos contenedores separados (la arquitectura actual), que es el approach recomendado hasta que haya demanda real de esta feature.

---

### F-06 🟡 — Panel de Estado Minimal (Status Endpoint)
**Prioridad: Media** · Esfuerzo estimado: Medio

Micro-servidor FastAPI (~100 líneas) que expone `/status` en JSON:

```json
{
  "provider": "simkl",
  "bsky_handle": "@devorando-series.bsky.social",
  "last_post": "2026-10-01T10:27:50Z",
  "next_check_in": "83 minutes",
  "token_valid": true,
  "streak": 47,
  "announced_total": 18432,
  "pending_triggers": []
}
```

Útil para OliveTin, Homepage dashboard y monitorización desde el móvil sin revisar logs.

---

### F-07 🟡 — Hilos de Comentarios / Mini-críticas por Capítulo (Thread Mode)
**Prioridad: Media** · Esfuerzo estimado: Medio

Poder adjuntar reflexiones, comentarios personales o mini-críticas a un capítulo específico y que se publiquen como respuesta encadenada (hilo nativo en Bluesky / AT Protocol) al post principal del scrobble.

**Análisis de Solución Arquitectónica:**
Dado que ni SIMKL ni WeTrakr ofrecen una interfaz fluida para redactar notas privadas por episodio desde el salón, se evalúan 4 opciones:

1. **Vía Nativa Bluesky (Recomendada - Cero fricción / Cero código):**
   * El scrobbler publica el post como `@devorando-series.bsky.social`.
   * En la app oficial de Bluesky del móvil (que permite alternar cuentas con 1 toque), pulsas "Responder" a tu propio post de scrobble.
   * *Ventajas:* Ya es un hilo nativo de Bluesky, soporta texto largo, imágenes, facetas y formato rico sin añadir código, servidores ni APIs intermedias.

2. **Vía OliveTin (`cmd.insaid.net`) — Formulario Rápido Web:**
   * El scrobbler almacena en `state.json` los metadatos de publicación del último post: `{ "uri": at://..., "cid": ..., "title": "Severance 2x01" }`.
   * En el panel de OliveTin (`cmd.insaid.net`), una acción "Comentar último episodio" muestra el título actual y un campo de texto multilínea.
   * Al enviar, ejecuta `post_thread_reply.py "<comentario>"` que usa `reply_to={"root": uri, "parent": uri}` en AT Protocol.
   * *Ventajas:* Acceso directo web desde móvil sin necesidad de interactuar en la app de Bluesky.

3. **Vía Telegram Bot (Descartada por sobrecarga):**
   * Recibir aviso en Telegram al scrobblear y responder con el comentario. Requiere un listener persistente (webhook/long-polling), gestión de sesiones y dependencias externas que añaden complejidad innecesaria.

4. **Vía API de Comentarios de SIMKL:**
   * SIMKL dispone de endpoint `/comments` en su API. Si el usuario publica un comentario al marcar el episodio en SIMKL, el scrobbler lo consulta en el siguiente ciclo y lo replica como hilo en Bluesky.

---

## ⬜ Descartado / No aplica

| Feature | Motivo |
|:--------|:-------|
| **Webhook receiver** | No aplica: la demora de 90min es deseable para agrupar visualizaciones |
| **Post "Empezando a ver" (1x01)** | No tiene sentido con 90min de demora; se publicaría junto al post de fin de episodio |
| **Trakt.tv como tercer proveedor** | Limitación de su API a una sola app; plataforma en decadencia |
| **Telegram Bot para comentarios** | Demasiada sobrecarga y puntos de fallo frente a la app nativa o OliveTin |
| **Refactoring arquitectónico** | Deuda técnica real pero baja prioridad. Pendiente para cuando haya contribuidores externos |
| **Tests automatizados** | Mismo criterio que el refactoring. Prioritario antes de hacer el repo público con contribuciones |

---

## 📊 Tabla de Priorización Global

| ID | Tipo | Descripción | Prioridad | Esfuerzo | Versión target |
|:---|:-----|:------------|:----------|:---------|:---------------|
| PC-01 | Bug latente | At-least-once delivery (doble post tras crash) | 🔴 Alta | Alto | v1.1 |
| PC-02 | Bug latente | Rate limiting Bluesky (backlog flood) | 🔴 Alta | Bajo | v1.1 |
| F-01 | Feature | Resumen Anual con collage | 🟡 Alta | Medio | v1.1 |
| F-02 | Feature | Rate Limiter configurable | 🟡 Alta | Bajo | v1.1 |
| PC-03 | Bug latente | Deduplicación anime/shows SIMKL | 🟡 Media | Bajo | v1.1 |
| PC-04 | Bug latente | Rotación fun fact no determinista | 🟡 Media | Bajo | v1.1 |
| PC-05 | Bug latente | Alerta si token expira definitivamente | 🟡 Media | Bajo | v1.1 |
| F-03 | Feature | Post de valoración explícita | 🟡 Media | Medio | v1.2 |
| F-07 | Feature | Hilos de comentarios / mini-críticas | 🟡 Media | Bajo | v1.2 |
| F-04 | Feature | Fun fact: Cementerio de Dropped | 🟡 Media | Bajo | v1.2 |
| F-06 | Feature | Panel de estado JSON `/status` | 🟡 Media | Medio | v1.2 |
| F-05 | Feature | Multi-cuenta nativa | 🟢 Baja | Alto | v1.3+ |

---

## 🏗️ Deuda Técnica (backlog a largo plazo)

> No urgente. A abordar antes de aceptar contribuciones externas o hacer el proyecto verdaderamente público.

- **Modularizar `app/`**: separar en `providers/`, `publishers/`, `core/`
- **Tests unitarios**: mínimo `test_storage.py` (PC-01), `test_evaluate_season_status.py` (la función más compleja del proyecto) y `test_phrases.py`  
- **Validación de secretos al arranque**: `startup_check()` que valide formato de tokens antes de iniciar el bucle principal
- **Migración de `state.json`**: sistema de versiones para el formato del estado (`"schema_version": 2`) que permita migraciones automáticas sin perder datos

---

*Documento mantenido por [@insaid-code](https://github.com/insaid-code) · Contribuciones bienvenidas via Issues y Pull Requests.*
