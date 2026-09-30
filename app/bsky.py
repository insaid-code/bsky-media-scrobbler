import logging
import requests
from atproto import Client, models

log = logging.getLogger("simkl-bluesky")


class BlueskyPublisher:
    def __init__(self, handle: str, app_password: str, lang: str | None = None, dry_run: bool = False):
        self.handle = handle.strip() if handle else ""
        self.app_password = app_password.strip() if app_password else ""
        self.langs = [lang.strip()] if lang else ["es"]
        self.dry_run = dry_run
        self.client = Client()
        self._logged_in = False

    def login(self):
        if self.dry_run:
            log.info("[DRY-RUN] Modo simulación activo: omitiendo login real en Bluesky para @%s.", self.handle or "test")
            self._logged_in = True
            return

        try:
            log.info("Iniciando sesión en Bluesky como @%s...", self.handle)
            self.client.login(self.handle, self.app_password)
            self._logged_in = True
            log.info("Sesión iniciada con éxito en Bluesky.")
        except Exception as e:
            self._logged_in = False
            log.error("Error al autenticar en Bluesky: %s", e)
            raise

    def ensure_login(self):
        if not self._logged_in:
            self.login()

    def post_watch(
        self,
        text: str,
        link_url: str | None = None,
        title: str | None = None,
        description: str | None = None,
        poster_url: str | None = None,
        image_bytes: bytes | None = None,
        image_alt: str = "Collage de carátulas",
    ) -> bool:
        """
        Publica en Bluesky un post con tarjeta enriquecida (External Embed)
        o una imagen compuesta adjunta (Image Embed). En DRY-RUN solo simula en log.
        """
        if self.dry_run:
            log.info("[DRY-RUN] Simulación de Bluit (NO publicado en Bluesky):")
            log.info("-----------------------------------------------------------------")
            for line in text.split("\n"):
                log.info("  %s", line)
            if link_url:
                log.info("[DRY-RUN] Ficha externa (Card): %s (Título: %s)", link_url, title)
            if poster_url:
                log.info("[DRY-RUN] Carátula externa: %s", poster_url)
            if image_bytes:
                log.info("[DRY-RUN] Imagen adjunta (Collage/Blob): %d bytes (Alt: %s)", len(image_bytes), image_alt)
            log.info("-----------------------------------------------------------------")
            return True

        self.ensure_login()

        embed = None
        if image_bytes:
            try:
                upload = self.client.upload_blob(image_bytes)
                embed = models.AppBskyEmbedImages.Main(
                    images=[
                        models.AppBskyEmbedImages.Image(
                            alt=image_alt,
                            image=upload.blob,
                        )
                    ]
                )
                log.info("Imagen adjunta subida a Bluesky con éxito (%d bytes).", len(image_bytes))
            except Exception as img_err:
                log.warning("No se pudo subir la imagen a Bluesky: %s", img_err)

        elif link_url:
            thumb_blob = None
            if poster_url:
                try:
                    resp = requests.get(poster_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=15)
                    if resp.status_code == 200 and resp.content:
                        upload = self.client.upload_blob(resp.content)
                        thumb_blob = upload.blob
                        log.info("Carátula subida a Bluesky con éxito (%d bytes).", len(resp.content))
                    else:
                        log.warning("Fallo al descargar carátula %s: status %s", poster_url, resp.status_code)
                except Exception as e:
                    log.warning("No se pudo procesar la carátula para Bluesky: %s", e)

            embed = models.AppBskyEmbedExternal.Main(
                external=models.AppBskyEmbedExternal.External(
                    title=title or "Ver detalles",
                    description=description or "",
                    uri=link_url,
                    thumb=thumb_blob,
                )
            )

        # Límite estricto de AT Protocol (Bluesky): máximo 300 grafemas
        if len(text) > 300:
            log.warning("El texto del post supera los 300 caracteres (%d). Recortando de forma segura...", len(text))
            text = text[:296] + "..."

        try:
            # send_post analiza y añade automáticamente las facetas para hashtags y menciones
            self.client.send_post(text=text, embed=embed, langs=self.langs)
            log.info("Publicación enviada a Bluesky: %s", text.splitlines()[0])
            return True
        except Exception as e:
            log.error("Fallo al enviar post a Bluesky: %s", e)
            # Reintentar login por si la sesión caducó
            try:
                self.login()
                self.client.send_post(text=text, embed=embed, langs=self.langs)
                log.info("Publicación enviada tras reautenticación.")
                return True
            except Exception as retry_err:
                log.error("Fallo definitivo al publicar en Bluesky: %s", retry_err)
                return False

