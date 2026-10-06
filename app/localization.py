import logging
from tvdb import TVDBClient
from storage import Storage

log = logging.getLogger("bsky-media-scrobbler")


class TitleResolver:
    """
    Resuelve títulos localizados de series, anime y películas según el idioma configurado.
    - En español ('es') y catalán ('ca'): busca la traducción oficial en castellano ('spa') en TheTVDB v4.
    - En inglés ('en'): mantiene el título original sin realizar llamadas de red.
    - Utiliza una caché persistente en disco (Storage) para que cada obra solo se consulte 1 vez
      en toda su vida útil.
    """

    def __init__(
        self,
        storage: Storage,
        tvdb_client: TVDBClient | None = None,
        lang: str = "es",
    ):
        self.storage = storage
        self.tvdb = tvdb_client
        self.lang = lang.lower() if lang else "es"

    def resolve(
        self,
        media_type: str,
        item_data: dict,
        default_title: str,
    ) -> str:
        # Si el idioma es inglés u otro distinto a es/ca, o no hay TheTVDB configurado, usar original
        if self.lang not in ("es", "ca") or not self.tvdb or not self.tvdb.is_configured:
            return default_title

        ids = item_data.get("ids") or {}
        item_id = ids.get("simkl") or ids.get("wetrakr") or ids.get("tmdb") or ids.get("tvdb")
        tvdb_id = ids.get("tvdb")
        imdb_id = ids.get("imdb")

        # 1. Comprobar caché persistente en disco (0 ms)
        cached = self.storage.get_localized_title(media_type, item_id, tvdb_id=tvdb_id, lang="es")
        if cached:
            return cached

        # 2. Consultar TheTVDB v4 (español 'spa')
        resolved_title = None
        target_tvdb_lang = "spa"

        try:
            # Si no hay tvdb_id directo pero sí IMDb, resolver remoteId
            if not tvdb_id and imdb_id:
                tvdb_id = self.tvdb.search_remote_id(imdb_id)

            if tvdb_id:
                if media_type == "movies":
                    resolved_title = self.tvdb.get_movie_translation(tvdb_id, lang=target_tvdb_lang)
                else:
                    resolved_title = self.tvdb.get_series_translation(tvdb_id, lang=target_tvdb_lang)

            if resolved_title:
                log.info("🌐 Título localizado con TheTVDB: '%s' -> '%s'", default_title, resolved_title)
                final_title = resolved_title
            else:
                log.debug("TheTVDB no tiene traducción en castellano para '%s' (id: %s). Usando título original.", default_title, tvdb_id)
                final_title = default_title

            # Guardar en caché permanente para no volver a consultar en próximos capítulos
            self.storage.set_localized_title(
                media_type=media_type,
                item_id=item_id,
                title=final_title,
                tvdb_id=tvdb_id,
                lang="es",
            )
            return final_title

        except Exception as e:
            log.warning("Fallo al consultar traducción en TheTVDB para '%s': %s", default_title, e)
            # En caso de error puntual de red, no se cachea permanentemente para permitir reintentar
            return default_title
