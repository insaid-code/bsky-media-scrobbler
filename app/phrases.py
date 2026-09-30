import copy
import json
import logging
import os
import random
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

LOCALES_DIR = Path(__file__).resolve().parent / "locales"
DEFAULT_CUSTOM_PATH = Path("/data/custom_phrases.json")


class SafeDict(dict):
    """Diccionario que devuelve '{key}' si la clave no existe, evitando KeyErrors en plantillas."""

    def __missing__(self, key):
        return "{" + key + "}"


def safe_format(template: str, **kwargs) -> str:
    """Interpola variables en la plantilla de forma segura ante claves no proporcionadas."""
    try:
        return template.format_map(SafeDict(**kwargs))
    except Exception:
        return template


def choose_fresh(options: list[str], recent_phrases: list[str] | None = None) -> str:
    """
    Selecciona una frase aleatoria descartando las que hayan sido usadas recientemente
    para garantizar cero repeticiones.
    """
    if not options:
        return ""
    if not recent_phrases:
        return random.choice(options)

    def get_prefix(text: str) -> str:
        return text.split(":")[0].strip()

    recent_prefixes = {get_prefix(p) for p in recent_phrases}
    fresh_options = [opt for opt in options if get_prefix(opt) not in recent_prefixes]

    if fresh_options:
        return random.choice(fresh_options)
    return random.choice(options)


class PhraseLoader:
    """
    Cargador reactivo de frases multilingües con soporte para frases personalizadas
    y recarga en caliente (hot-reload sin reiniciar contenedor).
    """

    def __init__(self, locales_dir: Path = LOCALES_DIR, custom_path: Path | None = None):
        self.locales_dir = locales_dir
        self.custom_path = (
            custom_path
            or Path(os.getenv("CUSTOM_PHRASES_PATH", str(DEFAULT_CUSTOM_PATH)))
        )
        self._base_cache: dict[str, dict] = {}
        self._custom_mtime: float | None = -1.0
        self._custom_data: dict = {}
        self._merged_cache: dict[str, dict] = {}

    def _load_base_locale(self, lang: str) -> dict:
        if lang in self._base_cache:
            return self._base_cache[lang]

        file_path = self.locales_dir / f"{lang}.json"
        if not file_path.exists():
            file_path = self.locales_dir / "es.json"

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            log.error("Error al cargar archivo de localización %s: %s", file_path, e)
            data = {}

        self._base_cache[lang] = data
        return data

    def _check_and_load_custom(self) -> None:
        try:
            if not self.custom_path.exists():
                if self._custom_mtime != -1.0:
                    self._custom_mtime = -1.0
                    self._custom_data = {}
                    self._merged_cache.clear()
                return

            mtime = self.custom_path.stat().st_mtime
            if mtime != self._custom_mtime:
                self._custom_mtime = mtime
                with open(self.custom_path, "r", encoding="utf-8") as f:
                    self._custom_data = json.load(f)
                self._merged_cache.clear()
                log.info("Cargadas frases personalizadas actualizadas desde %s", self.custom_path)
        except Exception as e:
            log.warning("No se pudieron cargar frases personalizadas desde %s: %s", self.custom_path, e)

    def _merge_dict(self, base: dict, custom: dict, replace_keys: set, prefix: str = "") -> dict:
        merged = copy.deepcopy(base)
        for k, v in custom.items():
            if k in ("replace", "replace_categories", "_comment", "_instructions"):
                continue
            cur_path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                if v.get("replace") is True and "phrases" in v and isinstance(v["phrases"], list):
                    merged[k] = list(v["phrases"])
                else:
                    base_sub = merged.get(k, {}) if isinstance(merged.get(k), dict) else {}
                    merged[k] = self._merge_dict(base_sub, v, replace_keys, cur_path)
            elif isinstance(v, list):
                if cur_path in replace_keys:
                    merged[k] = list(v)
                else:
                    existing = merged.get(k, [])
                    if isinstance(existing, list):
                        merged[k] = existing + list(v)
                    else:
                        merged[k] = list(v)
            else:
                merged[k] = v
        return merged

    def get_data(self, lang: str | None = None) -> dict:
        target_lang = lang or os.getenv("BSKY_LANG", "es")
        self._check_and_load_custom()

        if target_lang in self._merged_cache:
            return self._merged_cache[target_lang]

        base = self._load_base_locale(target_lang)
        if not self._custom_data:
            self._merged_cache[target_lang] = base
            return base

        replace_keys = set(self._custom_data.get("replace", [])) | set(
            self._custom_data.get("replace_categories", [])
        )
        merged = self._merge_dict(base, self._custom_data, replace_keys)
        self._merged_cache[target_lang] = merged
        return merged


phrase_loader = PhraseLoader()


class DynamicEngagementQuestions(dict):
    """Acceso dinámico y retrocompatible a ENGAGEMENT_QUESTIONS."""

    def __getitem__(self, key):
        data = phrase_loader.get_data().get("engagement_questions", {})
        return data.get(key, [])

    def get(self, key, default=None):
        data = phrase_loader.get_data().get("engagement_questions", {})
        return data.get(key, default)

    def __contains__(self, key):
        return key in phrase_loader.get_data().get("engagement_questions", {})


ENGAGEMENT_QUESTIONS = DynamicEngagementQuestions()


def get_engagement_question(category: str, lang: str | None = None) -> str:
    """Devuelve una pregunta aleatoria de conversación para la categoría indicada."""
    data = phrase_loader.get_data(lang)
    options = data.get("engagement_questions", {}).get(category, [])
    return random.choice(options) if options else ""


def get_show_phrase(
    show_title: str,
    range_label: str,
    season_num: int,
    first_ep: int,
    last_ep: int,
    real_max_ep: int,
    is_finale: bool,
    user_rating: float | int | None = None,
    recent_phrases: list[str] | None = None,
    is_backlog_rescue: bool = False,
    backlog_days: int = 0,
    tz_name: str = "Europe/Madrid",
    is_latest_aired: bool = False,
    lang: str | None = None,
    tracker_name: str = "SIMKL",
) -> tuple[str, str | None]:
    """
    Genera un encabezado dinámico y fresco mediante una bolsa combinada que evalúa:
    - Final de temporada (prioridad absoluta + llamada a conversación)
    - Al día con la emisión / último emitido (prioridad para series en emisión semanal/activa)
    - Rescate de backlog (> 1.5 años en pausa)
    - Volumen de la sesión: capítulo único, doble sesión (2), maratón (3), mega-maratón (4+)
    - Hitos de temporada: inicio de serie, inicio de temporada, ecuador, penúltimo, recta final
    - Franja horaria: madrugada, mañana, sobremesa/tarde, noche/prime time
    - Día de la semana: lunes, miércoles/jueves, viernes, sábado, domingo
    - Progreso general
    """
    data = phrase_loader.get_data(lang)
    shows_data = data.get("shows", {})
    labels = data.get("labels", {})

    try:
        now = datetime.now(ZoneInfo(tz_name))
        current_hour = now.hour
        current_weekday = now.weekday()
    except Exception:
        now = datetime.now()
        current_hour = now.hour
        current_weekday = now.weekday()

    ep_count = last_ep - first_ep + 1
    months = max(backlog_days // 30, 18)
    years = round(backlog_days / 365, 1)

    ctx = {
        "show_title": show_title,
        "range_label": range_label,
        "season_num": season_num,
        "first_ep": first_ep,
        "last_ep": last_ep,
        "real_max_ep": real_max_ep,
        "ep_count": ep_count,
        "user_rating": user_rating if user_rating is not None else "",
        "backlog_days": backlog_days,
        "months": months,
        "years": years,
        "tracker_name": tracker_name,
    }

    # 1. FINAL DE TEMPORADA (Hito principal)
    if is_finale:
        finale_options = shows_data.get("finale", [])
        formatted_options = [safe_format(opt, **ctx) for opt in finale_options]
        rating_parts = []
        if user_rating:
            rating_parts.append(
                safe_format(
                    labels.get("rating_show", "⭐ Mi valoración: {user_rating}/10"),
                    **ctx,
                )
            )
        q = get_engagement_question("finale", lang=lang)
        if q:
            rating_parts.append(q)
        rating_line = "\n\n".join(rating_parts) if rating_parts else None
        return choose_fresh(formatted_options, recent_phrases), rating_line

    # 2. AL DÍA CON LA EMISIÓN / ÚLTIMO EMITIDO (Series en emisión activa)
    if is_latest_aired:
        cu_data = shows_data.get("caught_up", {})
        if ep_count >= 4:
            caught_up_options = cu_data.get("marathon_4", [])
        elif ep_count == 3:
            caught_up_options = cu_data.get("triple_3", [])
        elif ep_count == 2:
            caught_up_options = cu_data.get("double_2", [])
        else:
            caught_up_options = cu_data.get("single_1", [])
        formatted_options = [safe_format(opt, **ctx) for opt in caught_up_options]
        return choose_fresh(formatted_options, recent_phrases), None

    # 3. BOLSA COMBINADA PARA EL RESTO DE SITUACIONES
    candidates: list[str] = []

    # Rescate del Backlog (> 1.5 años / 547 días sin visionado de esta serie)
    if is_backlog_rescue and backlog_days >= 547:
        candidates.extend(shows_data.get("backlog_rescue", []))

    # A) Volumen de la sesión
    vol_data = shows_data.get("volume", {})
    if ep_count >= 4:
        candidates.extend(vol_data.get("mega_4", []))
    elif ep_count == 3:
        candidates.extend(vol_data.get("triple_3", []))
    elif ep_count == 2:
        candidates.extend(vol_data.get("double_2", []))

    # B) Hitos de temporada
    milestones_data = shows_data.get("season_milestones", {})
    if first_ep == 1:
        if season_num == 1:
            candidates.extend(milestones_data.get("show_premiere", []))
        else:
            candidates.extend(milestones_data.get("season_premiere", []))
    elif real_max_ep > 0:
        if last_ep == real_max_ep - 1:
            candidates.extend(milestones_data.get("penultimate", []))
        elif last_ep >= real_max_ep - 2:
            candidates.extend(milestones_data.get("final_stretch", []))
        elif real_max_ep >= 6 and (real_max_ep // 2) in range(first_ep, last_ep + 1):
            candidates.extend(milestones_data.get("mid_season", []))

    # C) Franjas Horarias
    tod_data = shows_data.get("time_of_day", {})
    if 0 <= current_hour <= 5:
        candidates.extend(tod_data.get("night", []))
    elif 6 <= current_hour <= 11:
        candidates.extend(tod_data.get("morning", []))
    elif 14 <= current_hour <= 18:
        candidates.extend(tod_data.get("afternoon", []))
    elif 20 <= current_hour <= 23:
        candidates.extend(tod_data.get("evening", []))

    # D) Días de la semana
    dow_data = shows_data.get("day_of_week", {})
    if current_weekday == 0:
        candidates.extend(dow_data.get("monday", []))
    elif current_weekday in (2, 3):
        candidates.extend(dow_data.get("midweek", []))
    elif current_weekday == 4:
        candidates.extend(dow_data.get("friday", []))
    elif current_weekday == 5:
        candidates.extend(dow_data.get("saturday", []))
    elif current_weekday == 6:
        candidates.extend(dow_data.get("sunday", []))

    # E) Progreso habitual (fondo de catálogo constante)
    candidates.extend(shows_data.get("general", []))

    formatted_candidates = [safe_format(c, **ctx) for c in candidates]
    return choose_fresh(formatted_candidates, recent_phrases), None


def get_movie_phrase(
    movie_title: str,
    year: int | None,
    user_rating: float | int | None = None,
    recent_phrases: list[str] | None = None,
    tz_name: str = "Europe/Madrid",
    lang: str | None = None,
    tracker_name: str = "SIMKL",
) -> tuple[str, str | None]:
    """
    Genera un encabezado dinámico y variado para películas según:
    - Calificación destacada (>= 8.5) o baja (<= 5)
    - Época: clásicos (< 2000), estrenos recientes
    - Momento de visionado: madrugada, sobremesa, fin de semana, noche
    - Repertorio general enriquecido
    """
    data = phrase_loader.get_data(lang)
    movies_data = data.get("movies", {})
    labels = data.get("labels", {})

    try:
        now = datetime.now(ZoneInfo(tz_name))
        current_hour = now.hour
        current_weekday = now.weekday()
    except Exception:
        now = datetime.now()
        current_hour = now.hour
        current_weekday = now.weekday()

    is_night = 0 <= current_hour <= 5
    is_weekend = current_weekday in (4, 5, 6)
    year_str = f" ({year})" if year else ""
    current_year = datetime.now().year

    ctx = {
        "movie_title": movie_title,
        "year": year if year is not None else "",
        "year_str": year_str,
        "user_rating": user_rating if user_rating is not None else "",
        "tracker_name": tracker_name,
    }

    # 1. NOTA MUY ALTA (Joyas >= 8.5)
    if user_rating and user_rating >= 8.5:
        top_options = movies_data.get("top_rating", [])
        formatted_options = [safe_format(opt, **ctx) for opt in top_options]
        rating_str = safe_format(
            labels.get("rating_movie", "⭐ Mi valoración: {user_rating}/10"), **ctx
        )
        q = get_engagement_question("top_movie", lang=lang)
        rating_line = f"{rating_str}\n\n{q}" if q else rating_str
        return choose_fresh(formatted_options, recent_phrases), rating_line

    # 2. NOTA FLOJA (<= 5)
    if user_rating and user_rating <= 5:
        low_options = movies_data.get("low_rating", [])
        formatted_options = [safe_format(opt, **ctx) for opt in low_options]
        rating_line = safe_format(
            labels.get("rating_movie", "⭐ Mi valoración: {user_rating}/10"), **ctx
        )
        return choose_fresh(formatted_options, recent_phrases), rating_line

    # 3. BOLSA COMBINADA PARA PELÍCULAS
    candidates: list[str] = []

    # A) Por época
    era_data = movies_data.get("era", {})
    if year and year < 2000:
        candidates.extend(era_data.get("classic", []))
    elif year and year >= current_year - 1:
        candidates.extend(era_data.get("recent", []))

    # B) Por franja horaria
    tod_data = movies_data.get("time_of_day", {})
    if is_night:
        candidates.extend(tod_data.get("night", []))
    elif 14 <= current_hour <= 18:
        candidates.extend(tod_data.get("afternoon", []))
    elif 20 <= current_hour <= 23:
        candidates.extend(tod_data.get("evening", []))

    # C) Fin de semana
    if is_weekend:
        candidates.extend(movies_data.get("weekend", []))

    # D) Repertorio general variado
    candidates.extend(movies_data.get("general", []))

    formatted_candidates = [safe_format(c, **ctx) for c in candidates]
    rating_line = (
        safe_format(labels.get("rating_movie", "⭐ Mi valoración: {user_rating}/10"), **ctx)
        if user_rating
        else None
    )
    return choose_fresh(formatted_candidates, recent_phrases), rating_line
