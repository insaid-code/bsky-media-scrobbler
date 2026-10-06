import logging
import time
import requests

log = logging.getLogger("bsky-media-scrobbler")

TVDB_API_BASE = "https://api4.thetvdb.com/v4"


class TVDBClient:
    """
    Cliente para la API v4 oficial de TheTVDB.
    Permite autenticarse mediante API key y consultar traducciones localizadas
    de series y películas en español ('spa').
    """

    def __init__(self, api_key: str | None = None, session: requests.Session | None = None):
        self.api_key = api_key.strip() if api_key else ""
        self.session = session or requests.Session()
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def login(self) -> bool:
        """Autentica contra TheTVDB API v4 y obtiene un Bearer token."""
        if not self.api_key:
            return False

        # Si el token aún es válido (más de 24h restantes), reutilizarlo
        if self._token and time.time() < self._token_expires_at:
            return True

        url = f"{TVDB_API_BASE}/login"
        payload = {"apikey": self.api_key}
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "bsky-media-scrobbler/1.0",
        }

        try:
            resp = self.session.post(url, json=payload, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("data", {}).get("token")
                if token:
                    self._token = token
                    # TheTVDB JWT token dura 30 días; renovamos tras 25 días
                    self._token_expires_at = time.time() + (25 * 86400)
                    log.info("✅ Autenticación exitosa con TheTVDB v4.")
                    return True
            log.warning("Fallo al autenticar en TheTVDB v4: HTTP %d - %s", resp.status_code, resp.text)
        except Exception as e:
            log.warning("Error de conexión al autenticar en TheTVDB v4: %s", e)
        return False

    def _get(self, path: str, timeout: int = 15) -> requests.Response | None:
        """Realiza una petición GET autenticada a TheTVDB v4 con reintento si el token expira."""
        if not self.login():
            return None

        url = f"{TVDB_API_BASE}{path}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "User-Agent": "bsky-media-scrobbler/1.0",
        }

        try:
            resp = self.session.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 401:
                # Token expirado o revocado, re-login y reintentar una vez
                self._token = None
                if self.login():
                    headers["Authorization"] = f"Bearer {self._token}"
                    resp = self.session.get(url, headers=headers, timeout=timeout)
            return resp
        except Exception as e:
            log.debug("Error en petición a TheTVDB v4 (%s): %s", path, e)
            return None

    def get_series_translation(self, tvdb_id: str | int, lang: str = "spa") -> str | None:
        """
        Obtiene el título traducido de una serie en TheTVDB v4.
        Devuelve el nombre traducido o None si no existe traducción en ese idioma.
        """
        if not self.is_configured or not tvdb_id:
            return None

        path = f"/series/{tvdb_id}/translations/{lang}"
        resp = self._get(path)
        if resp and resp.status_code == 200:
            try:
                data = resp.json().get("data")
                if isinstance(data, dict):
                    name = data.get("name")
                    if name and name.strip():
                        return name.strip()
            except Exception as e:
                log.debug("Error al decodificar traducción de serie TVDB %s: %s", tvdb_id, e)
        return None

    def get_movie_translation(self, tvdb_id: str | int, lang: str = "spa") -> str | None:
        """
        Obtiene el título traducido de una película en TheTVDB v4.
        Devuelve el nombre traducido o None si no existe traducción en ese idioma.
        """
        if not self.is_configured or not tvdb_id:
            return None

        path = f"/movies/{tvdb_id}/translations/{lang}"
        resp = self._get(path)
        if resp and resp.status_code == 200:
            try:
                data = resp.json().get("data")
                if isinstance(data, dict):
                    name = data.get("name")
                    if name and name.strip():
                        return name.strip()
            except Exception as e:
                log.debug("Error al decodificar traducción de película TVDB %s: %s", tvdb_id, e)
        return None

    def search_remote_id(self, remote_id: str) -> str | int | None:
        """
        Busca un registro en TheTVDB usando un remoteId (ej: tt1234567 de IMDb).
        Devuelve el ID numérico de TheTVDB si se encuentra.
        """
        if not self.is_configured or not remote_id:
            return None

        path = f"/search/remoteid/{remote_id}"
        resp = self._get(path)
        if resp and resp.status_code == 200:
            try:
                body = resp.json()
                data = body.get("data")
                item = data[0] if isinstance(data, list) and data else (data if isinstance(data, dict) else None)
                if item:
                    tid = item.get("objectID") or item.get("id") or item.get("seriesId") or item.get("movieId")
                    if tid:
                        return tid
            except Exception as e:
                log.debug("Error al resolver remote_id %s en TheTVDB: %s", remote_id, e)
        return None
