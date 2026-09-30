import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

from bsky import BlueskyPublisher
from phrases import get_movie_phrase, get_show_phrase
from simkl import (
    SimklClient,
    episode_key,
    evaluate_season_status,
    format_episode_range,
    get_link_url,
    get_poster_url,
    get_show_episodes,
    group_consecutive_episodes,
    is_season_finale,
    movie_key,
    parse_iso,
)
from stats import StatsManager
from storage import Storage, now_iso
from wetrakr import WeTrakrClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("bsky-media-scrobbler")

# -----------------------------------------------------------------------------
# Configuración y Variables de Entorno
# -----------------------------------------------------------------------------
TRACKER_PROVIDER = os.getenv("TRACKER_PROVIDER", "simkl").lower().strip()
DRY_RUN = os.getenv("DRY_RUN", "false").lower().strip() in ("true", "1", "yes")

# WeTrakr
WETRAKR_CLIENT_ID = os.getenv("WETRAKR_CLIENT_ID") or os.getenv("WETRAKR_API_KEY")
WETRAKR_CLIENT_SECRET = os.getenv("WETRAKR_CLIENT_SECRET")
WETRAKR_ACCESS_TOKEN = os.getenv("WETRAKR_ACCESS_TOKEN")

# SIMKL
SIMKL_CLIENT_ID = os.getenv("SIMKL_CLIENT_ID")
SIMKL_USER_TOKEN = os.getenv("SIMKL_USER_TOKEN")

# Bluesky
BSKY_HANDLE = os.getenv("BSKY_HANDLE")
BSKY_APP_PASSWORD = os.getenv("BSKY_APP_PASSWORD")
BSKY_LANG = os.getenv("BSKY_LANG", "es")

# Detección de placeholders de plantilla en credenciales de Bluesky
if any(p in (BSKY_HANDLE or "").lower() for p in ("tu_cuenta", "tu_usuario", "ejemplo", "example", "placeholder")) or \
   any(p in (BSKY_APP_PASSWORD or "").lower() for p in ("tu_app_password", "tu_password", "placeholder")):
    log.warning("Detectadas credenciales de plantilla en Bluesky ('%s'). Activando DRY_RUN=True automáticamente para simulación segura.", BSKY_HANDLE)
    DRY_RUN = True

try:
    POLL_INTERVAL_MINUTES = max(int(os.getenv("POLL_INTERVAL_MINUTES", "90")), 5)
except ValueError:
    POLL_INTERVAL_MINUTES = 90

LINK_DESTINATION = os.getenv("LINK_DESTINATION", "tmdb").lower()
MEDIA_TYPES = ("shows", "movies") if TRACKER_PROVIDER == "wetrakr" else ("shows", "anime", "movies")
ACTIVITY_KEYS = {"shows": "tv_shows", "anime": "anime", "movies": "movies"}


def clean_hashtag(name: str) -> str:
    """Convierte un título en un hashtag válido de Bluesky."""
    if not name:
        return ""
    cleaned = "".join(c for c in name if c.isalnum())
    return f"#{cleaned}" if cleaned else ""


def get_platform_tags(link_dest: str, provider: str = "simkl") -> str:
    """Genera los hashtags de plataforma dinámicamente."""
    dest = link_dest.lower()
    tracker_tag = "#WeTrakr" if provider == "wetrakr" else "#Simkl"
    if dest == "tmdb":
        return f"#TMDB {tracker_tag}"
    if dest == "imdb":
        return f"#IMDb {tracker_tag}"
    if dest == "wetrakr":
        return "#WeTrakr"
    return tracker_tag


def seed_history_if_needed(client, storage: Storage, provider: str = "simkl"):
    """Siembra el historial inicial para no anunciar cosas del pasado."""
    if storage.is_seeded():
        return

    provider_name = "WeTrakr" if provider == "wetrakr" else "SIMKL"
    log.info("Iniciando siembra inicial de historial %s (para no publicar registros antiguos)...", provider_name)
    keys = []

    for media_type in MEDIA_TYPES:
        try:
            items = client.get_all_items(media_type)
            if media_type == "movies":
                for item in items or []:
                    movie = item.get("movie") or {}
                    ids = movie.get("ids") or {}
                    item_id = ids.get(provider) or ids.get("simkl") or ids.get("tmdb") or ids.get("wetrakr")
                    if item_id is not None:
                        keys.append(movie_key(media_type, item_id))
            else:
                for item in items or []:
                    show = item.get("show") or {}
                    ids = show.get("ids") or {}
                    item_id = ids.get(provider) or ids.get("simkl") or ids.get("tmdb") or ids.get("wetrakr")
                    if item_id is None:
                        continue
                    for season in item.get("seasons") or []:
                        s_num = season.get("number")
                        if s_num is None:
                            continue
                        for ep in season.get("episodes") or []:
                            ep_num = ep.get("number")
                            if ep_num is not None:
                                keys.append(episode_key(media_type, item_id, s_num, ep_num))
        except Exception as e:
            log.error("Error durante la siembra de %s: %s", media_type, e)

    storage.mark_seeded(keys)
    log.info("✅ Siembra completada: %d registros históricos guardados como anunciados.", len(keys))


def process_movies(items: list, storage: Storage, bsky: BlueskyPublisher, provider: str = "simkl"):
    announced = storage.get_announced()
    new_keys = []

    for item in items or []:
        movie = item.get("movie") or {}
        ids = movie.get("ids") or {}
        item_id = ids.get(provider) or ids.get("simkl") or ids.get("tmdb") or ids.get("wetrakr")
        if item_id is None:
            continue

        key = movie_key("movies", item_id)
        if key in announced:
            continue

        title = movie.get("title", "Película")
        year = movie.get("year")
        year_str = f" ({year})" if year else ""
        user_rating = item.get("user_rating")

        recent_phrases = storage.get_recent_phrases()
        tracker_label = "WeTrakr" if provider == "wetrakr" else "SIMKL"
        header_text, rating_line = get_movie_phrase(
            title,
            year,
            user_rating,
            recent_phrases=recent_phrases,
            lang=BSKY_LANG,
            tracker_name=tracker_label,
        )
        lines = [header_text]
        if rating_line:
            lines.append(rating_line)

        tag = clean_hashtag(title)
        tags_line = f"#Cine {tag} {get_platform_tags(LINK_DESTINATION, provider=provider)}".strip()
        lines.append(f"\n{tags_line}")

        post_text = "\n".join(lines)
        link_url = get_link_url("movies", movie, LINK_DESTINATION)
        poster_url = get_poster_url(movie.get("poster"))
        overview = movie.get("overview")

        if bsky.post_watch(
            text=post_text,
            link_url=link_url,
            title=f"{title}{year_str}",
            description=overview,
            poster_url=poster_url,
        ):
            new_keys.append(key)
            announced.add(key)
            storage.add_recent_phrase(header_text)
            time.sleep(3)  # Pausa de cortesía entre posts

    if new_keys:
        storage.add_announced(new_keys)
        log.info("Publicadas %d película(s) en Bluesky.", len(new_keys))


def process_shows(media_type: str, items: list, storage: Storage, bsky: BlueskyPublisher, provider: str = "simkl"):
    announced = storage.get_announced()
    new_keys = []

    for item in items or []:
        show = item.get("show") or {}
        ids = show.get("ids") or {}
        item_id = ids.get(provider) or ids.get("simkl") or ids.get("tmdb") or ids.get("wetrakr")
        if item_id is None:
            continue

        show_title = show.get("title", "Serie")
        tag = clean_hashtag(show_title)
        category_tag = "#Anime" if media_type == "anime" else "#Series"

        for season in item.get("seasons") or []:
            season_num = season.get("number")
            if season_num is None:
                continue

            # Buscar episodios nuevos no anunciados en esta temporada
            unannounced_eps = []
            for ep in season.get("episodes") or []:
                ep_num = ep.get("number")
                if ep_num is None:
                    continue
                k = episode_key(media_type, item_id, season_num, ep_num)
                if k not in announced and ep.get("watched_at"):
                    unannounced_eps.append({
                        "episode_number": ep_num,
                        "episode_title": ep.get("title"),
                        "key": k,
                    })

            if not unannounced_eps:
                continue

            # Agrupar episodios consecutivos (maratón)
            for ep_group in group_consecutive_episodes(unannounced_eps):
                watched_numbers = [e["episode_number"] for e in ep_group]
                first_ep = ep_group[0]
                last_ep = ep_group[-1]
                range_label = format_episode_range(season_num, first_ep["episode_number"], last_ep["episode_number"])

                # Comprobar si incluye final de temporada real o si queda al día con el último emitido
                is_finale, is_latest_aired, user_rating, real_max_ep = evaluate_season_status(
                    item, season_num, watched_numbers, SIMKL_CLIENT_ID if provider == "simkl" else None
                )

                # Detección de rescate de backlog (> 1.5 años / 547 días sin visionado)
                is_backlog = False
                backlog_days = 0
                prev_dates = []
                for s in item.get("seasons") or []:
                    s_idx = s.get("number")
                    for ep in s.get("episodes") or []:
                        e_idx = ep.get("number")
                        if ep.get("watched_at") and episode_key(media_type, item_id, s_idx, e_idx) in announced:
                            prev_dates.append(parse_iso(ep["watched_at"]))

                if prev_dates:
                    last_prev_dt = max(prev_dates)
                    now_utc = datetime.now(timezone.utc)
                    diff = (now_utc - last_prev_dt).days
                    if diff >= 547:
                        is_backlog = True
                        backlog_days = diff

                recent_phrases = storage.get_recent_phrases()
                tracker_label = "WeTrakr" if provider == "wetrakr" else "SIMKL"
                header_text, rating_line = get_show_phrase(
                    show_title=show_title,
                    range_label=range_label,
                    season_num=season_num,
                    first_ep=first_ep["episode_number"],
                    last_ep=last_ep["episode_number"],
                    real_max_ep=real_max_ep,
                    is_finale=is_finale,
                    user_rating=user_rating,
                    recent_phrases=recent_phrases,
                    is_backlog_rescue=is_backlog,
                    backlog_days=backlog_days,
                    is_latest_aired=is_latest_aired,
                    lang=BSKY_LANG,
                    tracker_name=tracker_label,
                )

                lines = [header_text]
                if rating_line:
                    lines.append(rating_line)
                elif len(ep_group) == 1 and first_ep.get("episode_title"):
                    lines.append(f"«{first_ep['episode_title']}»")

                tags_line = f"{category_tag} {tag} {get_platform_tags(LINK_DESTINATION, provider=provider)}".strip()
                lines.append(f"\n{tags_line}")

                post_text = "\n".join(lines)
                link_url = get_link_url(media_type, show, LINK_DESTINATION)
                poster_url = get_poster_url(show.get("poster"))
                overview = show.get("overview")

                if bsky.post_watch(
                    text=post_text,
                    link_url=link_url,
                    title=f"{show_title} - {range_label}",
                    description=overview,
                    poster_url=poster_url,
                ):
                    group_keys = [e["key"] for e in ep_group]
                    new_keys.extend(group_keys)
                    announced.update(group_keys)
                    storage.add_recent_phrase(header_text)
                    time.sleep(3)

    if new_keys:
        storage.add_announced(new_keys)
        log.info("Publicados %d episodio(s) de %s en Bluesky.", len(new_keys), media_type)


def check_triggers(stats_mgr: StatsManager):
    """Comprueba archivos de trigger manual en /data/ para ejecuciones inmediatas."""
    # 1. Trigger semanal forzado
    trig_weekly = "/data/trigger_weekly"
    if os.path.exists(trig_weekly):
        log.info("🔔 [TRIGGER] Detectada petición forzada de Resumen Semanal.")
        content = ""
        try:
            with open(trig_weekly, "r", encoding="utf-8") as f:
                content = f.read().strip()
            os.remove(trig_weekly)
        except Exception as e:
            log.warning("No se pudo leer/eliminar archivo trigger_weekly: %s", e)

        target_count = 4 if ("2x2" in content or "4" in content) else 9
        log.info("Ejecutando resumen semanal forzado (target_count=%d)...", target_count)
        try:
            stats_mgr.check_weekly(datetime.now(), force=True, target_count=target_count)
        except Exception as e:
            log.error("Error al ejecutar trigger semanal: %s", e, exc_info=True)

    # 2. Trigger mensual forzado
    trig_monthly = "/data/trigger_monthly"
    if os.path.exists(trig_monthly):
        log.info("🔔 [TRIGGER] Detectada petición forzada de Resumen Mensual.")
        content = ""
        try:
            with open(trig_monthly, "r", encoding="utf-8") as f:
                content = f.read().strip()
            os.remove(trig_monthly)
        except Exception as e:
            log.warning("No se pudo leer/eliminar archivo trigger_monthly: %s", e)

        target_count = 9 if ("3x3" in content or "9" in content) else 4
        log.info("Ejecutando resumen mensual forzado (target_count=%d)...", target_count)
        try:
            stats_mgr.check_monthly(datetime.now(), force=True, target_count=target_count)
        except Exception as e:
            log.error("Error al ejecutar trigger mensual: %s", e, exc_info=True)

    # 3. Trigger curiosidad / fun fact forzado
    trig_fun_fact = "/data/trigger_fun_fact"
    if os.path.exists(trig_fun_fact):
        log.info("🔔 [TRIGGER] Detectada petición forzada de Fun Fact / Curiosidad.")
        try:
            os.remove(trig_fun_fact)
        except Exception:
            pass
        try:
            stats_mgr.check_fun_fact(datetime.now(), force=True)
        except Exception as e:
            log.error("Error al ejecutar trigger fun_fact: %s", e, exc_info=True)


def main():
    log.info("Iniciando servicio bsky-media-scrobbler [Tracker: %s, Dry-Run: %s]...", TRACKER_PROVIDER.upper(), DRY_RUN)

    if not DRY_RUN and (not BSKY_HANDLE or not BSKY_APP_PASSWORD):
        log.critical("Faltan credenciales de Bluesky (BSKY_HANDLE o BSKY_APP_PASSWORD).")
        sys.exit(1)

    storage = Storage()

    # Inicialización del proveedor de seguimiento
    if TRACKER_PROVIDER == "wetrakr":
        if not WETRAKR_CLIENT_ID:
            log.critical("Falta WETRAKR_CLIENT_ID (o WETRAKR_API_KEY) en las variables de entorno.")
            sys.exit(1)

        stored_token_data = storage.get_wetrakr_token() or {}
        if isinstance(stored_token_data, str):
            stored_token_data = {"access_token": stored_token_data}

        token = WETRAKR_ACCESS_TOKEN or stored_token_data.get("access_token")
        refresh_token = stored_token_data.get("refresh_token")

        tracker_client = WeTrakrClient(
            client_id=WETRAKR_CLIENT_ID,
            client_secret=WETRAKR_CLIENT_SECRET,
            token=token,
            refresh_token=refresh_token,
            on_token_refreshed=storage.set_wetrakr_token,
        )

        if not token:
            log.info("No se ha configurado token de WeTrakr. Iniciando autorización PIN...")
            try:
                pin_data = tracker_client.start_device_flow()
                user_code = pin_data.get("user_code")
                device_code = pin_data.get("device_code")
                verification_url = (
                    pin_data.get("verification_url")
                    or pin_data.get("verification_uri")
                    or "https://wetrakr.com/activate"
                )
                expires_in = pin_data.get("expires_in", 900)
                interval = pin_data.get("interval", 5)

                log.info("=================================================================")
                log.info("👉 Entra en: %s", verification_url)
                log.info("👉 Introduce el código PIN: %s", user_code)
                log.info("=================================================================")

                elapsed = 0
                token_data = None
                while elapsed < expires_in:
                    time.sleep(interval)
                    elapsed += interval
                    token_data = tracker_client.poll_device_token(device_code)
                    if token_data:
                        log.info("✅ Autorización de WeTrakr completada con éxito.")
                        storage.set_wetrakr_token(token_data)
                        break

                if not token_data:
                    log.critical("El código PIN de WeTrakr ha caducado. Reinicia el contenedor.")
                    sys.exit(1)
            except Exception as e:
                log.critical("Error al iniciar autorización PIN de WeTrakr: %s", e)
                sys.exit(1)

    else:
        # Proveedor SIMKL (por defecto)
        if not SIMKL_CLIENT_ID:
            log.critical("Falta SIMKL_CLIENT_ID en las variables de entorno.")
            sys.exit(1)

        token = SIMKL_USER_TOKEN or storage.get_token()
        tracker_client = SimklClient(SIMKL_CLIENT_ID, token)

        if not token:
            log.info("No se ha configurado SIMKL_USER_TOKEN. Iniciando autorización PIN...")
            try:
                pin_data = tracker_client.start_device_flow()
                user_code = pin_data["user_code"]
                device_code = pin_data["device_code"]
                verification_url = pin_data.get("verification_uri", "https://simkl.com/pin")
                expires_in = pin_data.get("expires_in", 900)

                log.info("=================================================================")
                log.info("👉 Entra en: %s", verification_url)
                log.info("👉 Introduce el código: %s", user_code)
                log.info("=================================================================")

                elapsed = 0
                while elapsed < expires_in:
                    time.sleep(pin_data.get("interval", 5))
                    elapsed += 5
                    token = tracker_client.poll_device_token(device_code)
                    if token:
                        log.info("✅ Autorización de SIMKL completada con éxito.")
                        storage.set_token(token)
                        tracker_client.token = token
                        break

                if not token:
                    log.critical("El código PIN de SIMKL ha caducado. Reinicia el contenedor.")
                    sys.exit(1)
            except Exception as e:
                log.critical("Error al iniciar autorización PIN de SIMKL: %s", e)
                sys.exit(1)

    bsky = BlueskyPublisher(
        handle=BSKY_HANDLE or "dryrun-user",
        app_password=BSKY_APP_PASSWORD or "dryrun-pwd",
        lang=BSKY_LANG,
        dry_run=DRY_RUN,
    )
    bsky.login()

    stats_mgr = StatsManager(simkl=tracker_client, storage=storage, bsky=bsky, provider=TRACKER_PROVIDER)

    # Siembra inicial si es la primera vez
    seed_history_if_needed(tracker_client, storage, provider=TRACKER_PROVIDER)

    log.info("Iniciando bucle de comprobación cada %d minutos...", POLL_INTERVAL_MINUTES)

    while True:
        try:
            provider_label = "WeTrakr" if TRACKER_PROVIDER == "wetrakr" else "SIMKL"
            log.info("Comprobando nueva actividad en %s...", provider_label)
            activities = tracker_client.get_activities()

            for media_type in MEDIA_TYPES:
                act_key = ACTIVITY_KEYS.get(media_type, media_type)
                media_act = activities.get(act_key, {})
                last_server_time = media_act.get("all")
                last_local_time = storage.get_last_checked(media_type)

                # Si hay actividad posterior a la última comprobada
                if last_server_time and parse_iso(last_server_time) > parse_iso(last_local_time):
                    log.info("Detectada nueva actividad para '%s'. Obteniendo ítems...", media_type)
                    items = tracker_client.get_all_items(media_type, date_from=last_local_time)

                    if media_type == "movies":
                        process_movies(items, storage, bsky, provider=TRACKER_PROVIDER)
                    else:
                        process_shows(media_type, items, storage, bsky, provider=TRACKER_PROVIDER)

                    storage.set_last_checked(media_type, last_server_time)
                else:
                    log.debug("Sin nueva actividad en '%s'.", media_type)

            # Comprobar informes periódicos, rachas e hitos
            try:
                stats_mgr.check_all()
            except Exception as stats_err:
                log.warning("Aviso durante la comprobación de estadísticas: %s", stats_err)

        except Exception as e:
            log.error("Excepción durante la comprobación de %s: %s", provider_label, e, exc_info=True)

        log.info("Próxima comprobación en %d minutos.", POLL_INTERVAL_MINUTES)
        sleep_until = time.time() + (POLL_INTERVAL_MINUTES * 60)
        while time.time() < sleep_until:
            check_triggers(stats_mgr)
            time.sleep(5)


if __name__ == "__main__":
    main()
