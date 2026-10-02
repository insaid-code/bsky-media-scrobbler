import logging
import time
from datetime import datetime, timezone
import requests

log = logging.getLogger("bsky-media-scrobbler")

API_BASE = "https://api.wetrakr.com"
APP_NAME = "bsky-media-scrobbler"
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


class WeTrakrClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str | None = None,
        token: str | None = None,
        refresh_token: str | None = None,
        on_token_refreshed=None,
    ):
        self.client_id = client_id.strip() if client_id else ""
        self.client_secret = client_secret.strip() if client_secret else None
        self.token = token.strip() if token else None
        self.refresh_token_str = refresh_token.strip() if refresh_token else None
        self.on_token_refreshed = on_token_refreshed
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        # Q-03: Inicialización de cachés en __init__ (no lazy dentro de métodos)
        self._movie_cache: dict = {}
        self._show_cache: dict = {}
        self._dropped_cache: set = set()
        self._dropped_cache_time: float = 0.0

    def _headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "wetrakr-api-version": "1",
            "wetrakr-api-key": self.client_id,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    # -------------------------------------------------------------------------
    # Flujo de autorización PIN (Device Code Flow)
    # -------------------------------------------------------------------------
    def start_device_flow(self) -> dict:
        url = f"{API_BASE}/oauth/device/code"
        resp = self.session.post(
            url,
            headers={
                "Content-Type": "application/json",
                "wetrakr-api-version": "1",
                "wetrakr-api-key": self.client_id,
            },
            json={"client_id": self.client_id},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def poll_device_token(self, device_code: str) -> dict | None:
        url = f"{API_BASE}/oauth/device/token"
        body = {
            "code": device_code,
            "client_id": self.client_id,
        }
        if self.client_secret:
            body["client_secret"] = self.client_secret

        try:
            resp = self.session.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "wetrakr-api-version": "1",
                    "wetrakr-api-key": self.client_id,
                },
                json=body,
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                if "access_token" in data:
                    self.token = data["access_token"]
                    self.refresh_token_str = data.get("refresh_token")
                    return data
            return None
        except Exception as e:
            log.warning("Error durante sondeo de token de WeTrakr: %s", e)
            return None

    def refresh_access_token(self) -> bool:
        if not self.refresh_token_str:
            return False
        url = f"{API_BASE}/oauth/token/refresh"
        try:
            resp = self.session.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "wetrakr-api-version": "1",
                    "wetrakr-api-key": self.client_id,
                },
                json={
                    "refresh_token": self.refresh_token_str,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                if "access_token" in data:
                    self.token = data["access_token"]
                    if "refresh_token" in data:
                        self.refresh_token_str = data["refresh_token"]
                    if self.on_token_refreshed:
                        try:
                            self.on_token_refreshed({
                                "access_token": self.token,
                                "refresh_token": self.refresh_token_str,
                            })
                        except Exception as cb_err:
                            log.debug("Error en callback de token refreshed: %s", cb_err)
                    return True
        except Exception as e:
            log.error("Error al refrescar token de WeTrakr: %s", e)
        return False

    # -------------------------------------------------------------------------
    # Sondeo de actividad reciente
    # -------------------------------------------------------------------------
    def get_activities(self) -> dict:
        """Consulta los timestamps de los últimos cambios en la cuenta."""
        url = f"{API_BASE}/sync/last_activities"
        try:
            resp = self.session.get(url, headers=self._headers(), timeout=15)
            if resp.status_code == 401 and self.refresh_token_str:
                if self.refresh_access_token():
                    resp = self.session.get(url, headers=self._headers(), timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                shows_act = data.get("shows", {})
                movies_act = data.get("movies", {})
                episodes_act = data.get("episodes", {})
                ep_or_show = episodes_act.get("all") or shows_act.get("all") or data.get("all")
                movies_time = movies_act.get("all") or data.get("all")
                global_all = data.get("all") or ep_or_show or movies_time
                return {
                    "all": global_all,
                    "shows": {"all": ep_or_show},
                    "tv_shows": {"all": ep_or_show},
                    "anime": {"all": None},
                    "movies": {"all": movies_time},
                }
        except Exception as e:
            log.warning("No se pudieron obtener actividades de WeTrakr: %s", e)
        return {}

    # -------------------------------------------------------------------------
    # Consulta de detalles con caché para pósters y metadatos
    # -------------------------------------------------------------------------
    def get_movie_details(self, movie_id: int | str) -> dict:
        if not movie_id:
            return {}
        if movie_id in self._movie_cache:
            return self._movie_cache[movie_id]
        url = f"{API_BASE}/movies/{movie_id}"
        try:
            resp = self.session.get(url, headers=self._headers(), timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                self._movie_cache[movie_id] = data
                return data
        except Exception as e:
            log.debug("No se pudieron obtener detalles de la película %s de WeTrakr: %s", movie_id, e)
        return {}

    def get_show_details(self, show_id: int | str) -> dict:
        if not show_id:
            return {}
        if show_id in self._show_cache:
            return self._show_cache[show_id]
        url = f"{API_BASE}/shows/{show_id}"
        try:
            resp = self.session.get(url, headers=self._headers(), timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                self._show_cache[show_id] = data
                return data
        except Exception as e:
            log.debug("No se pudieron obtener detalles de la serie %s de WeTrakr: %s", show_id, e)
        return {}

    # -------------------------------------------------------------------------
    # Historial de visionados normalizado
    # -------------------------------------------------------------------------
    def get_all_items(self, media_type: str, date_from: str | None = None, **kwargs) -> list:
        """
        Obtiene el historial de visionados y lo normaliza a la estructura
        esperada por el motor de publicación.
        """
        if media_type == "movies":
            target = "movies"
            ext = "movie_level_2"
        else:
            target = "episodes"
            ext = "episode_level_2"

        url = f"{API_BASE}/sync/tracking/watched/history/{target}"
        params = {"extended": ext, "limit": 100}
        if date_from:
            params["from_date"] = date_from

        try:
            resp = self.session.get(url, headers=self._headers(), params=params, timeout=30)
            if resp.status_code == 401 and self.refresh_token_str:
                if self.refresh_access_token():
                    resp = self.session.get(url, headers=self._headers(), params=params, timeout=30)
            resp.raise_for_status()
            plays = resp.json()
            if not isinstance(plays, list):
                return []

            if media_type == "movies":
                normalized = []
                for p in plays:
                    mov = p.get("movie") or {}
                    ids = mov.get("ids") or {}
                    m_id = mov.get("id")

                    normalized.append({
                        "movie": {
                            "title": mov.get("title") or "Película",
                            "year": mov.get("year"),
                            "ids": {
                                "simkl": ids.get("tmdb") or m_id,
                                "tmdb": ids.get("tmdb"),
                                "imdb": ids.get("imdb"),
                                "wetrakr": m_id,
                            },
                            "poster": mov.get("poster_path"),
                            "overview": mov.get("overview"),
                            "runtime": mov.get("runtime"),
                        },
                        "watched_at": p.get("watched_at"),
                        "last_watched_at": p.get("watched_at"),
                    })
                return normalized
            else:
                shows_map = {}
                for p in plays:
                    ep = p.get("episode") or {}
                    show = ep.get("show") or {}
                    s_id = show.get("id") or (show.get("ids") or {}).get("tmdb")
                    if not s_id:
                        continue
                    if s_id not in shows_map:
                        s_ids = show.get("ids") or {}
                        show_poster = show.get("poster_path") or ep.get("season_poster_path")
                        show_overview = show.get("overview") or ep.get("overview")
                        show_runtime = show.get("runtime")

                        shows_map[s_id] = {
                            "show": {
                                "title": show.get("title") or "Serie",
                                "ids": {
                                    "simkl": s_ids.get("tmdb") or s_id,
                                    "tmdb": s_ids.get("tmdb"),
                                    "imdb": s_ids.get("imdb"),
                                    "wetrakr": s_id,
                                },
                                "poster": show_poster,
                                "overview": show_overview,
                                "runtime": show_runtime,
                            },
                            "seasons_dict": {},
                        }

                    s_num = ep.get("season_number") or 1
                    ep_num = ep.get("number")
                    if ep_num is not None:
                        s_dict = shows_map[s_id]["seasons_dict"].setdefault(s_num, [])
                        s_dict.append({
                            "number": ep_num,
                            "title": ep.get("title"),
                            "watched_at": p.get("watched_at"),
                        })

                dropped_ids = self.get_dropped_show_ids()
                res = []
                for item in shows_map.values():
                    s_ids = (item.get("show") or {}).get("ids") or {}
                    s_id = s_ids.get("wetrakr")
                    tmdb_id = s_ids.get("tmdb")
                    is_dropped = (s_id in dropped_ids) or (tmdb_id in dropped_ids)
                    status = "dropped" if is_dropped else "watching"

                    seasons_list = []
                    for s_num, eps in item["seasons_dict"].items():
                        seasons_list.append({
                            "number": s_num,
                            "episodes": eps,
                        })
                    res.append({
                        "show": item["show"],
                        "status": status,
                        "seasons": seasons_list,
                    })
                return res

        except Exception as e:
            log.warning("No se pudo obtener historial de WeTrakr para %s: %s", media_type, e)
            return []

    def get_dropped_show_ids(self) -> set:
        """Obtiene el conjunto de IDs (WeTrakr y TMDB) de series marcadas como dropped."""
        now = time.time()
        if now - self._dropped_cache_time > 300:
            self._dropped_cache = set()
            try:
                url = f"{API_BASE}/sync/tracking/dropped/shows"
                resp = self.session.get(url, headers=self._headers(), params={"limit": 100}, timeout=15)
                if resp.status_code == 401 and self.refresh_token_str:
                    if self.refresh_access_token():
                        resp = self.session.get(url, headers=self._headers(), params={"limit": 100}, timeout=15)
                if resp.status_code == 200:
                    for s in resp.json():
                        if s.get("id"):
                            self._dropped_cache.add(s["id"])
                            self._dropped_cache.add(str(s["id"]))
                        tmdb = (s.get("ids") or {}).get("tmdb")
                        if tmdb:
                            self._dropped_cache.add(tmdb)
                            self._dropped_cache.add(str(tmdb))
            except Exception as e:
                log.debug("No se pudieron obtener series dropped de WeTrakr: %s", e)
            self._dropped_cache_time = now
        return self._dropped_cache

    def get_dropped_shows(self) -> list[dict]:
        """Devuelve la lista completa de series descartadas (dropped) para futuros análisis."""
        try:
            url = f"{API_BASE}/sync/tracking/dropped/shows"
            resp = self.session.get(url, headers=self._headers(), params={"limit": 100}, timeout=15)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            log.debug("Error al obtener lista de dropped shows: %s", e)
        return []

    def get_user_stats(self) -> dict:
        url = f"{API_BASE}/account/stats/all"
        try:
            resp = self.session.get(url, headers=self._headers(), timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    w_time = data.get("watched_time") or {}
                    tracking = data.get("tracking") or {}
                    m_tracking = tracking.get("movies") or {}
                    s_tracking = tracking.get("shows") or {}
                    e_tracking = tracking.get("episodes") or {}

                    total_mins = int(w_time.get("minutes") or 0)
                    eps_watched = int(w_time.get("episodes_unique") or e_tracking.get("watched") or 0)
                    shows_completed = int(s_tracking.get("watched") or 0)
                    shows_watching = int(s_tracking.get("watching") or 0)
                    movies_completed = int(m_tracking.get("watched") or 0)

                    # Estructura normalizada compatible con StatsManager
                    return {
                        "total_mins": total_mins,
                        "tv": {
                            "completed": {
                                "count": shows_completed,
                                "watched_episodes_count": eps_watched,
                            },
                            "watching": {
                                "count": shows_watching,
                                "watched_episodes_count": 0,
                            },
                        },
                        "anime": {
                            "completed": {"count": 0, "watched_episodes_count": 0},
                            "watching": {"count": 0, "watched_episodes_count": 0},
                        },
                        "movies": {
                            "completed": {
                                "count": movies_completed,
                            }
                        },
                        "raw_wetrakr": data,
                    }
        except Exception as e:
            log.warning("Error al consultar estadísticas en WeTrakr: %s", e)
        return {}
