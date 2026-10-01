import logging
import time
from datetime import datetime, timezone
import requests

log = logging.getLogger("simkl-bluesky")

API_BASE = "https://api.simkl.com"
APP_NAME = "simkl-bluesky"
APP_VERSION = "1.0.0"
USER_AGENT = f"{APP_NAME}/{APP_VERSION}"


def parse_iso(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


class SimklClient:
    def __init__(
        self,
        client_id: str,
        token: str | None = None,
        refresh_token: str | None = None,
        on_token_refreshed=None,
    ):
        self.client_id = client_id.strip() if client_id else ""
        self.token = token.strip() if token else None
        self.refresh_token_str = refresh_token.strip() if refresh_token else None
        self.on_token_refreshed = on_token_refreshed
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def _headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "simkl-api-key": self.client_id,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _params(self, **extra) -> dict:
        return {
            "client_id": self.client_id,
            "app-name": APP_NAME,
            "app-version": APP_VERSION,
            **extra,
        }

    # -------------------------------------------------------------------------
    # Flujo de autenticación PIN (Device Auth) por si no se especifica token
    # -------------------------------------------------------------------------
    def start_device_flow(self) -> dict:
        url = f"{API_BASE}/oauth2/device"
        data = {
            "client_id": self.client_id,
            "scope": "media:read",
            "app-name": APP_NAME,
            "app-version": APP_VERSION,
        }
        resp = self.session.post(url, data=data)
        resp.raise_for_status()
        return resp.json()

    def poll_device_token(self, device_code: str) -> dict | None:
        url = f"{API_BASE}/oauth2/token"
        data = {
            "client_id": self.client_id,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code,
            "app-name": APP_NAME,
            "app-version": APP_VERSION,
        }
        resp = self.session.post(url, data=data)
        if resp.status_code == 200:
            body = resp.json()
            return {
                "access_token": body.get("access_token"),
                "refresh_token": body.get("refresh_token"),
            }
        return None

    def refresh_access_token(self) -> bool:
        """Renueva el access_token de SIMKL utilizando el refresh_token almacenado."""
        if not self.refresh_token_str:
            log.warning("No hay refresh_token disponible para renovar token de SIMKL.")
            return False

        url = f"{API_BASE}/oauth2/token"
        data = {
            "client_id": self.client_id,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token_str,
            "app-name": APP_NAME,
            "app-version": APP_VERSION,
        }
        try:
            resp = self.session.post(url, data=data, timeout=15)
            if resp.status_code == 200:
                body = resp.json()
                new_acc = body.get("access_token")
                new_ref = body.get("refresh_token") or self.refresh_token_str
                if new_acc:
                    self.token = new_acc
                    self.refresh_token_str = new_ref
                    log.info("Token de acceso de SIMKL renovado con éxito mediante refresh_token.")
                    if self.on_token_refreshed:
                        self.on_token_refreshed({
                            "access_token": new_acc,
                            "refresh_token": new_ref,
                        })
                    return True
            log.error("Fallo al renovar token de SIMKL: HTTP %d - %s", resp.status_code, resp.text)
        except Exception as e:
            log.error("Excepción al renovar token de SIMKL: %s", e)
        return False

    def _get(self, url: str, params: dict | None = None, timeout: int = 30) -> requests.Response:
        """Realiza una petición GET autenticada con reintento automático si expira el token."""
        resp = self.session.get(url, headers=self._headers(), params=params, timeout=timeout)
        if resp.status_code == 401 and self.refresh_token_str:
            log.info("Token de SIMKL caducado (401). Intentando renovación automática...")
            if self.refresh_access_token():
                resp = self.session.get(url, headers=self._headers(), params=params, timeout=timeout)
        return resp

    # -------------------------------------------------------------------------
    # API endpoints principales
    # -------------------------------------------------------------------------
    def get_activities(self) -> dict:
        """Obtiene las marcas de tiempo de la última actividad del usuario."""
        url = f"{API_BASE}/sync/activities"
        resp = self._get(url, params=self._params(), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_all_items(self, media_type: str, date_from: str | None = None) -> list:
        """
        Obtiene los ítems de series, anime o películas.
        Con date_from solo devuelve lo modificado/visto a partir de esa fecha.
        """
        url = f"{API_BASE}/sync/all-items/{media_type}"
        params = self._params(extended="full", episode_watched_at="yes")
        if date_from:
            params["date_from"] = date_from

        resp = self._get(url, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, dict):
            return data.get(media_type, [])
        return data or []

    def get_user_stats(self, user_id: str | int | None = None) -> dict:
        """Obtiene las estadísticas globales de visionado del usuario desde SIMKL."""
        if not user_id:
            try:
                settings_resp = self._get(
                    f"{API_BASE}/users/settings",
                    params=self._params(),
                    timeout=15,
                )
                if settings_resp.status_code == 200:
                    user_id = settings_resp.json().get("account", {}).get("id")
            except Exception as e:
                log.debug("No se pudo obtener account ID para stats: %s", e)
            if not user_id:
                user_id = 8077243

        try:
            url = f"{API_BASE}/users/{user_id}/stats"
            resp = self._get(url, params=self._params(), timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    return data
        except Exception as e:
            log.warning("Error al consultar estadísticas de usuario en SIMKL: %s", e)
        return {}


# -----------------------------------------------------------------------------
# Funciones auxiliares para procesar episodios y maratones
# -----------------------------------------------------------------------------
def episode_key(media_type: str, simkl_id: int | str, season_num: int, ep_num: int) -> str:
    return f"{media_type}:{simkl_id}:{season_num}:{ep_num}"


def movie_key(media_type: str, simkl_id: int | str) -> str:
    return f"{media_type}:{simkl_id}"


def format_episode_range(season_number: int | None, start_ep: int, end_ep: int) -> str:
    if season_number is None:
        if start_ep == end_ep:
            return f"E{start_ep:02d}"
        return f"E{start_ep:02d}–E{end_ep:02d}"

    if start_ep == end_ep:
        return f"S{season_number:02d}E{start_ep:02d}"
    return f"S{season_number:02d}E{start_ep:02d}–E{end_ep:02d}"


def group_consecutive_episodes(episodes: list[dict]) -> list[list[dict]]:
    """Agrupa episodios consecutivos en tandas de maratón."""
    if not episodes:
        return []

    episodes = sorted(episodes, key=lambda x: x["episode_number"])
    groups = []
    current = [episodes[0]]

    for ep in episodes[1:]:
        if ep["episode_number"] == current[-1]["episode_number"] + 1:
            current.append(ep)
        else:
            groups.append(current)
            current = [ep]

    groups.append(current)
    return groups


SHOW_EPISODES_CACHE = {}
SHOW_DETAILS_CACHE = {}


def get_show_episodes(simkl_id: int | str, client_id: str) -> list[dict]:
    """Obtiene y cachea la lista completa de episodios de una serie desde SIMKL."""
    simkl_id_int = int(simkl_id) if str(simkl_id).isdigit() else simkl_id
    if simkl_id_int in SHOW_EPISODES_CACHE:
        return SHOW_EPISODES_CACHE[simkl_id_int]
    try:
        resp = requests.get(
            f"{API_BASE}/tv/episodes/{simkl_id_int}",
            params={"client_id": client_id},
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                SHOW_EPISODES_CACHE[simkl_id_int] = data
                return data
    except Exception as e:
        log.warning("No se pudieron obtener episodios para simkl_id %s: %s", simkl_id, e)
    return []


def get_show_details(simkl_id: int | str, client_id: str) -> dict:
    """Obtiene y cachea los detalles y estado (airing, ended, etc.) de una serie desde SIMKL."""
    simkl_id_int = int(simkl_id) if str(simkl_id).isdigit() else simkl_id
    if simkl_id_int in SHOW_DETAILS_CACHE:
        return SHOW_DETAILS_CACHE[simkl_id_int]
    try:
        resp = requests.get(
            f"{API_BASE}/tv/{simkl_id_int}",
            params={"client_id": client_id},
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                SHOW_DETAILS_CACHE[simkl_id_int] = data
                return data
    except Exception as e:
        log.warning("No se pudieron obtener detalles para simkl_id %s: %s", simkl_id, e)
    return {}


def evaluate_season_status(
    item: dict,
    season_num: int,
    watched_ep_numbers: list[int],
    client_id: str,
) -> tuple[bool, bool, int | float | None, int]:
    """
    Evalúa con precisión si la tanda de episodios vista corresponde a:
    1. Un FINAL DE TEMPORADA real (is_finale=True).
    2. El ÚLTIMO CAPÍTULO EMITIDO hasta la fecha en una serie en emisión (is_latest_aired=True).
    3. Progreso estándar dentro de la temporada (ambos False).

    Devuelve: (is_finale, is_latest_aired, user_rating, real_max_ep)
    """
    show = item.get("show") or {}
    ids = show.get("ids") or {}
    simkl_id = ids.get("simkl")
    user_rating = item.get("user_rating") or show.get("user_rating")

    if not simkl_id or not client_id or not watched_ep_numbers:
        return False, False, user_rating, 0

    all_eps = get_show_episodes(simkl_id, client_id)
    if not all_eps:
        return False, False, user_rating, 0

    show_details = get_show_details(simkl_id, client_id)
    show_status = (show_details.get("status") or "").lower()

    # Identificar todas las temporadas conocidas en el catálogo
    catalog_seasons = sorted(set(
        e.get("season") for e in all_eps
        if isinstance(e.get("season"), int) and e.get("season") > 0
    ))
    max_catalog_season = max(catalog_seasons) if catalog_seasons else season_num

    # Episodios de la temporada evaluada
    season_eps = [
        e for e in all_eps
        if e.get("season") == season_num and isinstance(e.get("episode"), int)
    ]
    if not season_eps:
        return False, False, user_rating, 0

    max_catalog_ep = max((e.get("episode", 0) for e in season_eps), default=0)
    if max_catalog_ep == 0:
        return False, False, user_rating, 0

    # Episodios que ya han sido emitidos oficialmente
    now_utc = datetime.now(timezone.utc)
    aired_season_eps = [
        e for e in season_eps
        if e.get("aired") is True or (e.get("date") and parse_iso(e.get("date")) <= now_utc)
    ]
    max_aired_ep = max((e.get("episode", 0) for e in aired_season_eps), default=0)

    watched_max = max(watched_ep_numbers)
    reached_catalog_end = (watched_max >= max_catalog_ep)
    has_unaired_in_season = (max_catalog_ep > max_aired_ep)

    is_finale = False
    is_latest_aired = False
    real_max_ep = max_catalog_ep

    if reached_catalog_end:
        # A) Serie finalizada o cancelada: el último episodio del catálogo es final definitivo
        if show_status in ("ended", "canceled"):
            is_finale = True
        # B) Temporada previa ya concluida (existen temporadas posteriores en el catálogo)
        elif season_num < max_catalog_season:
            is_finale = True
        # C) Serie en emisión ('airing') en su temporada más reciente
        elif show_status == "airing" and season_num >= max_catalog_season:
            if has_unaired_in_season:
                is_finale = False
            else:
                last_ep_obj = next((e for e in season_eps if e.get("episode") == max_catalog_ep), None)
                last_air_dt = parse_iso(last_ep_obj.get("date")) if last_ep_obj else None
                days_since_air = (now_utc - last_air_dt).days if last_air_dt and last_air_dt != datetime.min.replace(tzinfo=timezone.utc) else None

                # Si se emitió recientemente (<= 30 días), la temporada sigue en curso semanal.
                # NO es final de temporada; no se conoce aún el número total de episodios.
                if days_since_air is not None and days_since_air <= 30:
                    is_finale = False
                    real_max_ep = 0
                elif days_since_air is not None and days_since_air > 30 and max_catalog_ep >= 3:
                    is_finale = True
                else:
                    is_finale = False
                    real_max_ep = 0
        else:
            if season_num < max_catalog_season:
                is_finale = True

    # Si no es final de temporada, verificar si ha quedado al día con el último emitido
    if not is_finale:
        if show_status == "airing" and season_num >= max_catalog_season:
            # En series en emisión donde los episodios se suben sobre la marcha
            if max_catalog_ep <= max_aired_ep:
                real_max_ep = 0
            if max_aired_ep > 0 and watched_max >= max_aired_ep:
                is_latest_aired = True

    return is_finale, is_latest_aired, user_rating, real_max_ep


def is_season_finale(item: dict, season_num: int, watched_ep_numbers: list[int], client_id: str) -> tuple[bool, int | float | None]:
    """Compatibilidad hacia atrás con firma original."""
    is_fin, _, rating, _ = evaluate_season_status(item, season_num, watched_ep_numbers, client_id)
    return is_fin, rating


def get_poster_url(poster_path: str | None) -> str | None:
    if not poster_path:
        return None
    if poster_path.startswith("/"):
        return f"https://image.tmdb.org/t/p/w500{poster_path}"
    if poster_path.startswith("http://") or poster_path.startswith("https://"):
        return poster_path
    return f"https://simkl.in/posters/{poster_path}_m.jpg"


def get_link_url(media_type: str, item_obj: dict, link_destination: str = "imdb") -> str:
    """Devuelve el enlace hacia IMDb, TMDB, WeTrakr o SIMKL según preferencia y disponibilidad."""
    ids = item_obj.get("ids") or {}
    imdb_id = ids.get("imdb")
    tmdb_id = ids.get("tmdb")
    simkl_id = ids.get("simkl")
    wetrakr_id = ids.get("wetrakr") or tmdb_id
    slug = ids.get("slug")

    dest = link_destination.lower()
    if dest == "tmdb" and tmdb_id:
        if media_type == "movies":
            return f"https://www.themoviedb.org/movie/{tmdb_id}"
        return f"https://www.themoviedb.org/tv/{tmdb_id}"

    if dest == "imdb" and imdb_id:
        return f"https://www.imdb.com/title/{imdb_id}/"

    if dest == "wetrakr" and wetrakr_id:
        if media_type == "movies":
            return f"https://wetrakr.com/movies/{wetrakr_id}"
        return f"https://wetrakr.com/shows/{wetrakr_id}"

    # Enlace a SIMKL si simkl_id está disponible
    if simkl_id:
        if media_type == "movies":
            base = "https://simkl.com/movies"
        elif media_type == "anime":
            base = "https://simkl.com/anime"
        else:
            base = "https://simkl.com/tv"

        if slug:
            return f"{base}/{simkl_id}/{slug}"
        return f"{base}/{simkl_id}"

    # Fallbacks si no hay SIMKL (ej. WeTrakr standalone)
    if tmdb_id:
        if media_type == "movies":
            return f"https://www.themoviedb.org/movie/{tmdb_id}"
        return f"https://www.themoviedb.org/tv/{tmdb_id}"

    if wetrakr_id:
        if media_type == "movies":
            return f"https://wetrakr.com/movies/{wetrakr_id}"
        return f"https://wetrakr.com/shows/{wetrakr_id}"

    if imdb_id:
        return f"https://www.imdb.com/title/{imdb_id}/"

    return ""

