import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from bsky import BlueskyPublisher
from collage import create_poster_collage
from phrases import get_engagement_question
from simkl import SimklClient, get_poster_url, parse_iso
from storage import Storage

log = logging.getLogger("simkl-bluesky")

MONTH_NAMES = {
    "es": [
        "",
        "Enero",
        "Febrero",
        "Marzo",
        "Abril",
        "Mayo",
        "Junio",
        "Julio",
        "Agosto",
        "Septiembre",
        "Octubre",
        "Noviembre",
        "Diciembre",
    ],
    "en": [
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ],
    "ca": [
        "",
        "Gener",
        "Febrer",
        "Març",
        "Abril",
        "Maig",
        "Juny",
        "Juliol",
        "Agost",
        "Setembre",
        "Octubre",
        "Novembre",
        "Desembre",
    ],
}

WEEKDAY_NAMES = {
    "es": [
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
    ],
    "en": [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ],
    "ca": [
        "Dilluns",
        "Dimarts",
        "Dimecres",
        "Dijous",
        "Divendres",
        "Dissabte",
        "Diumenge",
    ],
}


class StatsManager:
    def __init__(
        self,
        simkl,
        storage: Storage,
        bsky: BlueskyPublisher,
        tz_name: str = "Europe/Madrid",
        provider: str = "simkl",
        lang: str = "es",
    ):
        self.simkl = simkl
        self.storage = storage
        self.bsky = bsky
        self.tz_name = tz_name
        self.provider = provider
        self.lang = lang.lower() if lang else "es"
        self.tracker_tag = "#WeTrakr" if provider == "wetrakr" else "#Simkl"
        self.tracker_name = "WeTrakr" if provider == "wetrakr" else "SIMKL"

    def _now(self) -> datetime:
        try:
            return datetime.now(ZoneInfo(self.tz_name))
        except Exception:
            return datetime.now()

    def check_all(self):
        """Punto de entrada periódico para comprobar informes, rachas e hitos."""
        now = self._now()
        self.check_streaks(now)
        self.check_milestones(now)
        self.check_weekly(now)
        self.check_monthly(now)
        self.check_fun_fact(now)

    # -------------------------------------------------------------------------
    # 1. CONTADOR DE RACHAS (Streaks)
    # -------------------------------------------------------------------------
    def check_streaks(self, now: datetime):
        try:
            activities = self.simkl.get_activities()
            dates = []
            for k in ("tv_shows", "anime", "movies"):
                ts = activities.get(k, {}).get("all")
                if ts:
                    dates.append(parse_iso(ts))

            if not dates:
                return

            latest_activity = max(dates)
            activity_date_str = latest_activity.astimezone(ZoneInfo(self.tz_name)).strftime("%Y-%m-%d")

            current_streak, is_new_milestone = self.storage.record_activity_date(activity_date_str)

            if is_new_milestone and current_streak >= 7:
                log.info("🔥 ¡Nuevo hito de racha alcanzado!: %d días", current_streak)
                q = get_engagement_question("streak", lang=self.lang)
                if self.lang == "en":
                    text = (
                        f"🔥 NEW STREAK UNLOCKED! 🔥\n\n"
                        f"Just reached {current_streak} consecutive days watching movies and series.\n"
                        f"Consistency above all 📺🍿\n\n"
                        f"{q}\n"
                        f"#MediaStreak #TVShows #Cinema {self.tracker_tag} #TMDB"
                    )
                elif self.lang == "ca":
                    text = (
                        f"🔥 NOVA RATXA DESBLOQUEJADA! 🔥\n\n"
                        f"Acabo d'arribar als {current_streak} dies consecutius consumint ficció.\n"
                        f"La constància abans de tot 📺🍿\n\n"
                        f"{q}\n"
                        f"#RatxaSerèfila #Series #Cinema {self.tracker_tag} #TMDB"
                    )
                else:
                    text = (
                        f"🔥 ¡NUEVA RACHA DESBLOQUEADA! 🔥\n\n"
                        f"Acabo de alcanzar los {current_streak} días consecutivos consumiendo ficción.\n"
                        f"La constancia ante todo 📺🍿\n\n"
                        f"{q}\n"
                        f"#RachaSeriéfilo #Series #Cine {self.tracker_tag} #TMDB"
                    )
                self.bsky.post_watch(text=text)

        except Exception as e:
            log.warning("No se pudo verificar la racha: %s", e)

    # -------------------------------------------------------------------------
    # 2. HITOS HISTÓRICOS (Milestones)
    # -------------------------------------------------------------------------
    def check_milestones(self, now: datetime):
        try:
            stats = self.simkl.get_user_stats()
            if not stats:
                return

            tv = stats.get("tv", {})
            anime = stats.get("anime", {})
            movies = stats.get("movies", {})

            tv_watching_eps = tv.get("watching", {}).get("watched_episodes_count", 0)
            tv_completed_eps = tv.get("completed", {}).get("watched_episodes_count", 0)
            anime_watching_eps = anime.get("watching", {}).get("watched_episodes_count", 0)
            anime_completed_eps = anime.get("completed", {}).get("watched_episodes_count", 0)
            total_eps = tv_watching_eps + tv_completed_eps + anime_watching_eps + anime_completed_eps

            tv_completed_shows = tv.get("completed", {}).get("count", 0)
            movies_completed = movies.get("completed", {}).get("count", 0)
            total_mins = stats.get("total_mins", 0)
            total_hours = total_mins // 60

            celebrated = set(self.storage.get_celebrated_milestones())

            episode_milestones = [
                18000, 18500, 19000, 19500, 20000, 21000, 22000, 23000, 24000, 25000
            ]
            for m in episode_milestones:
                m_key = f"episodes:{m}"
                if total_eps >= m and m_key not in celebrated:
                    log.info("🎉 ¡Nuevo hito de episodios alcanzado!: %d episodios", m)
                    if self.lang == "en":
                        text = (
                            f"🎯 NEW MILESTONE UNLOCKED! 🎯\n\n"
                            f"Just reached {m:,} watched episodes in my history.\n\n"
                            f"📦 {tv_completed_shows} completed shows | 🎬 {movies_completed} movies\n"
                            f"⏳ Over {total_hours:,} hours of fiction on screen 🍿✨\n\n"
                            f"#MediaMilestone #TVShows {self.tracker_tag} #TMDB"
                        )
                    elif self.lang == "ca":
                        text = (
                            f"🎯 NOU HITO DESBLOQUEJAT! 🎯\n\n"
                            f"Acabo d'arribar als {m:,} episodis vistos al meu historial.\n\n"
                            f"📦 {tv_completed_shows} sèries al 100% | 🎬 {movies_completed} pel·lis\n"
                            f"⏳ Més de {total_hours:,} hores de ficció en pantalla 🍿✨\n\n"
                            f"#HitoSerèfil #Series {self.tracker_tag} #TMDB"
                        )
                    else:
                        text = (
                            f"🎯 ¡NUEVO HITO DESBLOQUEADO! 🎯\n\n"
                            f"Acabo de alcanzar los {m:,} episodios vistos en mi historial.\n\n"
                            f"📦 {tv_completed_shows} series al 100% | 🎬 {movies_completed} pelis\n"
                            f"⏳ Más de {total_hours:,} horas de ficción en pantalla 🍿✨\n\n"
                            f"#HitoSeriéfilo #Series {self.tracker_tag} #TMDB"
                        )
                    if self.bsky.post_watch(text=text):
                        self.storage.add_celebrated_milestone(m_key)
                    return

            show_milestones = [400, 425, 450, 475, 500, 550, 600]
            for m in show_milestones:
                m_key = f"shows_completed:{m}"
                if tv_completed_shows >= m and m_key not in celebrated:
                    log.info("🎉 ¡Nuevo hito de series completadas!: %d series", m)
                    if self.lang == "en":
                        text = (
                            f"🏆 COMPLETED SHOWS MILESTONE! 🏆\n\n"
                            f"That makes {m} shows completed from start to finish 100%.\n\n"
                            f"📺 {total_eps:,} total episodes watched\n"
                            f"🎬 {movies_completed} movies logged\n\n"
                            f"Finishing a whole series always leaves a void... what should I start next? 🍿\n"
                            f"#MediaMilestone #TVShows {self.tracker_tag} #TMDB"
                        )
                    elif self.lang == "ca":
                        text = (
                            f"🏆 HITO DE SÈRIES COMPLETADES! 🏆\n\n"
                            f"Ja són {m} sèries acabades de principi a fi al 100%.\n\n"
                            f"📺 {total_eps:,} episodis vistos en total\n"
                            f"🎬 {movies_completed} pel·lícules registrades\n\n"
                            f"Acabar una sèrie sencera sempre deixa un buit... quina començo ara? 🍿\n"
                            f"#HitoSerèfil #Series {self.tracker_tag} #TMDB"
                        )
                    else:
                        text = (
                            f"🏆 ¡HITO DE SERIES COMPLETADAS! 🏆\n\n"
                            f"Ya son {m} series terminadas de principio a fin al 100%.\n\n"
                            f"📺 {total_eps:,} episodios vistos en total\n"
                            f"🎬 {movies_completed} películas registradas\n\n"
                            f"Cerrar una serie entera siempre deja un vacío... ¿cuál empiezo ahora? 🍿\n"
                            f"#HitoSeriéfilo #Series {self.tracker_tag} #TMDB"
                        )
                    if self.bsky.post_watch(text=text):
                        self.storage.add_celebrated_milestone(m_key)
                    return

            movie_milestones = [450, 500, 550, 600, 700]
            for m in movie_milestones:
                m_key = f"movies_completed:{m}"
                if movies_completed >= m and m_key not in celebrated:
                    log.info("🎉 ¡Nuevo hito de películas alcanzado!: %d películas", m)
                    if self.lang == "en":
                        text = (
                            f"🎬 MOVIE MILESTONE UNLOCKED! 🎬\n\n"
                            f"Just reached {m} movies logged and watched.\n\n"
                            f"📺 Along with {total_eps:,} TV episodes\n"
                            f"⭐ Still discovering great stories on screen.\n\n"
                            f"#Cinema #Movies #MediaMilestone {self.tracker_tag} #TMDB"
                        )
                    elif self.lang == "ca":
                        text = (
                            f"🎬 HITO CINÈFIL DESBLOQUEJAT! 🎬\n\n"
                            f"Acabo d'arribar a les {m} pel·lícules vistes i registrades.\n\n"
                            f"📺 Acompanyades de {total_eps:,} capítols de sèries\n"
                            f"⭐ Continuem descobrint grans històries a la pantalla.\n\n"
                            f"#Cinema #Pel·lícules #HitoSerèfil {self.tracker_tag} #TMDB"
                        )
                    else:
                        text = (
                            f"🎬 ¡HITO CINÉFILO DESBLOQUEADO! 🎬\n\n"
                            f"Acabo de alcanzar las {m} películas vistas y registradas.\n\n"
                            f"📺 Acompañadas de {total_eps:,} capítulos de series\n"
                            f"⭐ Seguimos descubriendo grandes historias en la pantalla.\n\n"
                            f"#Cine #Películas #HitoSeriéfilo {self.tracker_tag} #TMDB"
                        )
                    if self.bsky.post_watch(text=text):
                        self.storage.add_celebrated_milestone(m_key)
                    return

        except Exception as e:
            log.warning("No se pudo comprobar hitos en SIMKL: %s", e)

    # -------------------------------------------------------------------------
    # 3. RESUMEN SEMANAL CON COLLAGE VISUAL (Lunes 09:30h+)
    # -------------------------------------------------------------------------
    def check_weekly(self, now: datetime, force: bool = False, target_count: int = 9):
        now_utc = now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)

        # Cálculo de la semana natural cerrada (Lunes 00:00:00 a Domingo 23:59:59):
        # Al publicar los lunes por la mañana, evaluamos la semana completa que concluyó ayer domingo a las 23:59:59.
        # En caso de ejecución forzada en cualquier otro día, se evalúa igualmente la última semana completa cerrada.
        days_since_sunday = now_utc.weekday() + 1
        end_dt = (now_utc - timedelta(days=days_since_sunday)).replace(hour=23, minute=59, second=59, microsecond=999999)
        start_dt = (end_dt - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        iso = end_dt.isocalendar()
        week_year = iso.year
        week_num = iso.week
        week_marker = f"{week_year}-W{week_num:02d}"

        if not force:
            # Publicación automática: Lunes a partir de las 09:30h
            if now.weekday() != 0 or now.hour < 9 or (now.hour == 9 and now.minute < 30):
                return
            if self.storage.get_last_stats_posted("weekly") == week_marker:
                return

        log.info("Generando informe semanal seriéfilo para la semana %s (%s a %s)...", week_marker, start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
        try:
            start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            shows_items = self.simkl.get_all_items("shows", date_from=start_iso) or []
            anime_items = self.simkl.get_all_items("anime", date_from=start_iso) or []
            movie_items = self.simkl.get_all_items("movies", date_from=start_iso) or []

            ep_counts_by_show = Counter()
            show_posters = {}
            total_eps = 0
            exact_watched_mins = 0

            for item in shows_items + anime_items:
                show = item.get("show") or {}
                show_title = show.get("title") or "Serie"
                ep_runtime = show.get("runtime") or 35
                eps_in_item = 0
                for season in item.get("seasons", []):
                    for ep in season.get("episodes", []):
                        w_at = ep.get("watched_at")
                        if w_at and start_dt <= parse_iso(w_at) <= end_dt:
                            eps_in_item += 1

                if eps_in_item > 0:
                    ep_counts_by_show[show_title] += eps_in_item
                    total_eps += eps_in_item
                    exact_watched_mins += (eps_in_item * ep_runtime)
                    p_url = get_poster_url(show.get("poster"))
                    if p_url and show_title not in show_posters:
                        show_posters[show_title] = p_url

            # Ordenar carátulas de series según volumen de episodios vistos
            sorted_show_posters = [
                show_posters[title]
                for title, _ in ep_counts_by_show.most_common()
                if title in show_posters
            ]

            movies_count = 0
            movie_posters = []
            for m in movie_items:
                w_at = m.get("last_watched_at") or m.get("watched_at")
                if w_at and start_dt <= parse_iso(w_at) <= end_dt:
                    movies_count += 1
                    movie = m.get("movie") or {}
                    m_runtime = movie.get("runtime") or 95
                    exact_watched_mins += m_runtime
                    p_url = get_poster_url(movie.get("poster"))
                    if p_url and p_url not in movie_posters:
                        movie_posters.append(p_url)

            # Prioridad y reparto inteligente de carátulas:
            # Las películas son visionados completos de ~2h y no deben quedar fuera por capítulos sueltos.
            if len(movie_posters) + len(sorted_show_posters) <= target_count:
                poster_urls = movie_posters + sorted_show_posters
            else:
                max_movies = min(len(movie_posters), (target_count + 1) // 2)
                selected_movies = movie_posters[:max_movies]
                remaining_slots = target_count - len(selected_movies)
                selected_shows = sorted_show_posters[:remaining_slots]
                if len(selected_shows) < remaining_slots and len(movie_posters) > len(selected_movies):
                    selected_movies += movie_posters[len(selected_movies):len(selected_movies) + (remaining_slots - len(selected_shows))]
                poster_urls = selected_movies + selected_shows

            if total_eps == 0 and movies_count == 0:
                self.storage.set_last_stats_posted("weekly", week_marker)
                return

            weekly_mins = exact_watched_mins
            if weekly_mins == 0:
                weekly_mins = (total_eps * 35) + (movies_count * 95)

            hours = weekly_mins // 60
            mins = weekly_mins % 60
            time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"

            top_show_str = ""
            if ep_counts_by_show:
                top_show, top_count = ep_counts_by_show.most_common(1)[0]
                if self.lang == "en":
                    top_show_str = f"\n🏆 Show of the week: {top_show} ({top_count} eps)"
                elif self.lang == "ca":
                    top_show_str = f"\n🏆 Sèrie de la setmana: {top_show} ({top_count} caps)"
                else:
                    top_show_str = f"\n🏆 Serie de la semana: {top_show} ({top_count} caps)"

            question = get_engagement_question("weekly", lang=self.lang)
            if self.lang == "en":
                movies_line = f"🎬 {movies_count} movie{'s' if movies_count != 1 else ''}\n" if movies_count > 0 else ""
                text = (
                    f"📊 Weekly Media Balance (Week {week_num})\n\n"
                    f"📺 {total_eps} episodes watched\n"
                    f"{movies_line}"
                    f"⏱️ {time_str} of screen time dedicated to fiction"
                    f"{top_show_str}\n\n"
                    f"{question}\n"
                    f"#Statistics #TVShows #Cinema {self.tracker_tag}"
                )
                alt_text = f"Weekly Collage {week_num}"
            elif self.lang == "ca":
                movies_line = f"🎬 {movies_count} pel·lícula{'s' if movies_count != 1 else ''}\n" if movies_count > 0 else ""
                text = (
                    f"📊 Balanç Setmanal Serèfil (Setmana {week_num})\n\n"
                    f"📺 {total_eps} episodis vistos\n"
                    f"{movies_line}"
                    f"⏱️ {time_str} de pantalla dedicats a la ficció"
                    f"{top_show_str}\n\n"
                    f"{question}\n"
                    f"#Estadístiques #Series #Cinema {self.tracker_tag}"
                )
                alt_text = f"Collage Setmanal {week_num}"
            else:
                movies_line = f"🎬 {movies_count} película{'s' if movies_count != 1 else ''}\n" if movies_count > 0 else ""
                text = (
                    f"📊 Balance Semanal Seriéfilo (Semana {week_num})\n\n"
                    f"📺 {total_eps} episodios vistos\n"
                    f"{movies_line}"
                    f"⏱️ {time_str} de pantalla dedicadas a la ficción"
                    f"{top_show_str}\n\n"
                    f"{question}\n"
                    f"#Estadísticas #Series #Cine {self.tracker_tag}"
                )
                alt_text = f"Collage Semanal {week_num}"

            collage_bytes = None
            if poster_urls:
                try:
                    collage_bytes = create_poster_collage(poster_urls, target_count=target_count)
                except Exception as c_err:
                    log.warning("No se pudo generar collage semanal: %s", c_err)

            if self.bsky.post_watch(text=text, image_bytes=collage_bytes, image_alt=alt_text):
                log.info("Publicado informe semanal con éxito (%s).", week_marker)
                self.storage.set_last_stats_posted("weekly", week_marker)

        except Exception as e:
            log.error("Error al generar resumen semanal: %s", e, exc_info=True)

    # -------------------------------------------------------------------------
    # 4. RESUMEN MENSUAL CON COLLAGE (Día 1 del mes 09:30h+)
    # -------------------------------------------------------------------------
    def check_monthly(self, now: datetime, force: bool = False, target_count: int = 4):
        now_utc = now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)

        # Cálculo del mes natural cerrado (Día 1 00:00:00 al último día 23:59:59):
        # Al publicar el día 1 de cada mes por la mañana, evaluamos el mes completo que concluyó ayer a las 23:59:59.
        first_of_this_month = now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_dt = first_of_this_month - timedelta(microseconds=1)
        start_dt = end_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_month = start_dt.month
        prev_year = start_dt.year
        month_marker = f"{prev_year}-{prev_month:02d}"

        if not force:
            # Publicación automática: Día 1 del mes a partir de las 09:30h
            if now.day != 1 or now.hour < 9 or (now.hour == 9 and now.minute < 30):
                return
            if self.storage.get_last_stats_posted("monthly") == month_marker:
                return

        log.info("Generando informe mensual seriéfilo para %s (%s a %s)...", month_marker, start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
        try:
            start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            shows_items = self.simkl.get_all_items("shows", date_from=start_iso) or []
            anime_items = self.simkl.get_all_items("anime", date_from=start_iso) or []
            movie_items = self.simkl.get_all_items("movies", date_from=start_iso) or []

            ep_counts_by_show = Counter()
            show_posters = {}
            total_eps = 0
            exact_watched_mins = 0
            completed_shows = []

            for item in shows_items + anime_items:
                show = item.get("show") or {}
                show_title = show.get("title") or "Serie"
                ep_runtime = show.get("runtime") or 35
                eps_in_item = 0
                for season in item.get("seasons", []):
                    for ep in season.get("episodes", []):
                        w_at = ep.get("watched_at")
                        if w_at and start_dt <= parse_iso(w_at) <= end_dt:
                            eps_in_item += 1

                if eps_in_item > 0:
                    ep_counts_by_show[show_title] += eps_in_item
                    total_eps += eps_in_item
                    exact_watched_mins += (eps_in_item * ep_runtime)
                    p_url = get_poster_url(show.get("poster"))
                    if p_url and show_title not in show_posters:
                        show_posters[show_title] = p_url

                if item.get("status") == "completed":
                    last_w = item.get("last_watched_at") or ""
                    if last_w:
                        try:
                            if start_dt <= parse_iso(last_w) <= end_dt:
                                completed_shows.append(show_title)
                        except Exception:
                            pass

            sorted_show_posters = [
                show_posters[title]
                for title, _ in ep_counts_by_show.most_common()
                if title in show_posters
            ]

            movies_count = 0
            movie_posters = []
            for m in movie_items:
                w_at = m.get("last_watched_at") or m.get("watched_at")
                if w_at and start_dt <= parse_iso(w_at) <= end_dt:
                    movies_count += 1
                    movie = m.get("movie") or {}
                    m_runtime = movie.get("runtime") or 95
                    exact_watched_mins += m_runtime
                    p_url = get_poster_url(movie.get("poster"))
                    if p_url and p_url not in movie_posters:
                        movie_posters.append(p_url)

            if total_eps == 0 and movies_count == 0:
                self.storage.set_last_stats_posted("monthly", month_marker)
                return

            monthly_mins = exact_watched_mins
            if monthly_mins == 0:
                monthly_mins = (total_eps * 35) + (movies_count * 95)

            hours = monthly_mins // 60
            mins = monthly_mins % 60
            time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"

            top_show_str = ""
            if ep_counts_by_show:
                top_show, top_count = ep_counts_by_show.most_common(1)[0]
                if self.lang == "en":
                    top_show_str = f"\n🏆 Show of the month: {top_show} ({top_count} eps)"
                elif self.lang == "ca":
                    top_show_str = f"\n🏆 Sèrie del mes: {top_show} ({top_count} caps)"
                else:
                    top_show_str = f"\n🏆 Serie del mes: {top_show} ({top_count} caps)"

            completed_str = ""
            if completed_shows:
                top_completed = completed_shows[:3]
                more = len(completed_shows) - len(top_completed)
                if self.lang == "en":
                    list_str = ", ".join(top_completed) + (f" (+{more} more)" if more > 0 else "")
                    completed_str = f"\n🏁 Completed shows: {list_str}"
                elif self.lang == "ca":
                    list_str = ", ".join(top_completed) + (f" (+{more} més)" if more > 0 else "")
                    completed_str = f"\n🏁 Sèries completades: {list_str}"
                else:
                    list_str = ", ".join(top_completed) + (f" (+{more} más)" if more > 0 else "")
                    completed_str = f"\n🏁 Series completadas: {list_str}"

            # Selección inteligente de carátulas para el collage (2x2 o 3x3 según target_count)
            if len(movie_posters) + len(sorted_show_posters) <= target_count:
                poster_urls = movie_posters + sorted_show_posters
            else:
                max_movies = min(len(movie_posters), (target_count + 1) // 2)
                selected_movies = movie_posters[:max_movies]
                remaining_slots = target_count - len(selected_movies)
                selected_shows = sorted_show_posters[:remaining_slots]
                if len(selected_shows) < remaining_slots and len(movie_posters) > len(selected_movies):
                    selected_movies += movie_posters[len(selected_movies):len(selected_movies) + (remaining_slots - len(selected_shows))]
                poster_urls = selected_movies + selected_shows

            month_name = MONTH_NAMES.get(self.lang, MONTH_NAMES["es"])[prev_month]
            question = get_engagement_question("monthly", lang=self.lang)

            if self.lang == "en":
                movies_line = f"🎬 {movies_count} movie{'s' if movies_count != 1 else ''}\n" if movies_count > 0 else ""
                text = (
                    f"🗓️ Monthly Media Balance ({month_name} {prev_year})\n\n"
                    f"📺 {total_eps} episodes binge-watched\n"
                    f"{movies_line}"
                    f"⏱️ {time_str} of screen time dedicated to fiction"
                    f"{top_show_str}"
                    f"{completed_str}\n\n"
                    f"{question}\n"
                    f"#MonthlyRecap #TVShows #Cinema {self.tracker_tag}"
                )
                alt_text = f"Monthly Collage {month_name} {prev_year}"
            elif self.lang == "ca":
                movies_line = f"🎬 {movies_count} pel·lícula{'s' if movies_count != 1 else ''}\n" if movies_count > 0 else ""
                text = (
                    f"🗓️ Balanç Mensual Serèfil ({month_name} {prev_year})\n\n"
                    f"📺 {total_eps} episodis devorats\n"
                    f"{movies_line}"
                    f"⏱️ {time_str} de pantalla dedicats a la ficció"
                    f"{top_show_str}"
                    f"{completed_str}\n\n"
                    f"{question}\n"
                    f"#ResumMensual #Series #Cinema {self.tracker_tag}"
                )
                alt_text = f"Collage Mensual {month_name} {prev_year}"
            else:
                movies_line = f"🎬 {movies_count} película{'s' if movies_count != 1 else ''}\n" if movies_count > 0 else ""
                text = (
                    f"🗓️ Balance Mensual Seriéfilo ({month_name} {prev_year})\n\n"
                    f"📺 {total_eps} episodios devorados\n"
                    f"{movies_line}"
                    f"⏱️ {time_str} de pantalla dedicadas a la ficción"
                    f"{top_show_str}"
                    f"{completed_str}\n\n"
                    f"{question}\n"
                    f"#ResumenMensual #Series #Cine {self.tracker_tag}"
                )
                alt_text = f"Collage Mensual {month_name} {prev_year}"

            collage_bytes = None
            if poster_urls:
                try:
                    collage_bytes = create_poster_collage(poster_urls, target_count=target_count)
                except Exception as c_err:
                    log.warning("No se pudo generar collage mensual: %s", c_err)

            if self.bsky.post_watch(text=text, image_bytes=collage_bytes, image_alt=alt_text):
                log.info("Publicado informe mensual con éxito (%s).", month_marker)
                self.storage.set_last_stats_posted("monthly", month_marker)

        except Exception as e:
            log.error("Error al generar resumen mensual: %s", e, exc_info=True)

    # -------------------------------------------------------------------------
    # 5. FUN FACTS Y CURIOSIDADES (Día 15 del mes 12:00h+)
    # -------------------------------------------------------------------------
    def check_fun_fact(self, now: datetime, force: bool = False):
        fact_marker = f"{now.year}-{now.month:02d}-15"
        if not force:
            if now.day != 15 or now.hour < 12:
                return
            if self.storage.get_last_stats_posted("fun_fact") == fact_marker:
                return

        log.info("Generando Fun Fact seriéfilo para %s...", fact_marker)
        try:
            topic = now.month % 3
            stats = self.simkl.get_user_stats()
            total_mins = stats.get("total_mins", 800000)
            tv = stats.get("tv", {})
            tv_completed = tv.get("completed", {}).get("count", 388)
            tv_watching = tv.get("watching", {}).get("count", 255)
            total_started = tv_completed + tv_watching

            text = ""

            # Tema 0: Día de la semana y patrón de visionado
            if topic == 0:
                try:
                    all_shows = self.simkl.get_all_items("shows") or []
                    weekdays = Counter()
                    hours = Counter()

                    for item in all_shows:
                        for season in item.get("seasons", []):
                            for ep in season.get("episodes", []):
                                w_at = ep.get("watched_at")
                                if w_at:
                                    dt = parse_iso(w_at)
                                    if dt.tzinfo:
                                        try:
                                            dt = dt.astimezone(ZoneInfo(self.tz_name))
                                        except Exception:
                                            pass
                                    weekdays[dt.weekday()] += 1
                                    hours[dt.hour] += 1

                    if weekdays:
                        top_wd, _ = weekdays.most_common(1)[0]
                        top_day_name = WEEKDAY_NAMES.get(self.lang, WEEKDAY_NAMES["es"])[top_wd]
                        top_hour, _ = hours.most_common(1)[0] if hours else (22, 0)
                        if self.lang == "en":
                            text = (
                                f"💡 Data Insight: Watching Habits on {self.tracker_name}\n\n"
                                f"📅 Favorite day: {top_day_name} is my most active day binge-watching.\n"
                                f"⏰ Peak time: My activity peaks around {top_hour:02d}:00.\n\n"
                                f"Do you also have a sacred day for watching shows? 📺🍿\n"
                                f"#Statistics #TVShows {self.tracker_tag}"
                            )
                        elif self.lang == "ca":
                            text = (
                                f"💡 Curiositat de Dades: Patrons a {self.tracker_name}\n\n"
                                f"📅 Dia preferit: El {top_day_name} és el meu dia més actiu fent maratons.\n"
                                f"⏰ Hora punta: La meva activitat sol concentrar-se cap a les {top_hour:02d}:00h.\n\n"
                                f"També teniu un dia sagrat per veure sèries? 📺🍿\n"
                                f"#Estadístiques #Series {self.tracker_tag}"
                            )
                        else:
                            text = (
                                f"💡 Curiosidad de Datos: Patrones en {self.tracker_name}\n\n"
                                f"📅 Día favorito: El {top_day_name} es mi día más activo maratoneando.\n"
                                f"⏰ Hora punta: Mi actividad suele concentrarse hacia las {top_hour:02d}:00h.\n\n"
                                f"¿Tenéis también un día sagrado para ver series? 📺🍿\n"
                                f"#Estadísticas #Series {self.tracker_tag}"
                            )
                except Exception as day_err:
                    log.warning("No se pudo calcular el patrón de días: %s", day_err)

            # Tema 1: La serie más larga completada
            if not text and (topic == 1 or topic == 0):
                try:
                    completed_shows = self.simkl.get_all_items("shows") or []
                    c_shows = [s for s in completed_shows if s.get("status") == "completed"]
                    if c_shows:
                        longest = max(c_shows, key=lambda x: x.get("watched_episodes_count", 0))
                        title = (longest.get("show") or {}).get("title") or "Serie"
                        ep_count = longest.get("watched_episodes_count", 0)

                        if self.lang == "en":
                            text = (
                                f"💡 Media Insight: Dedication\n\n"
                                f"Out of {tv_completed} shows completed 100%:\n"
                                f"🏆 The longest is {title} ({ep_count} episodes watched).\n\n"
                                f"What is the longest series you have ever finished? 🍿🎬\n"
                                f"#TVShows #Milestones {self.tracker_tag}"
                            )
                        elif self.lang == "ca":
                            text = (
                                f"💡 Curiositat Serèfila: Fidelitat\n\n"
                                f"De les {tv_completed} sèries acabades al 100%:\n"
                                f"🏆 La més extensa és {title} ({ep_count} capítols vistos).\n\n"
                                f"Quina és la sèrie més llarga que heu acabat? 🍿🎬\n"
                                f"#Series #Hitos {self.tracker_tag}"
                            )
                        else:
                            text = (
                                f"💡 Curiosidad Seriéfila: Fidelidad\n\n"
                                f"De las {tv_completed} series terminadas al 100%:\n"
                                f"🏆 La más extensa es {title} ({ep_count} capítulos vistos).\n\n"
                                f"¿Cuál es la serie más larga que habéis terminado? 🍿🎬\n"
                                f"#Series #Hitos {self.tracker_tag}"
                            )
                except Exception as long_err:
                    log.warning("No se pudo calcular la serie más larga: %s", long_err)

            # Tema 2 (Fallback): Tasa de finalización y tiempo global acumulado
            if not text:
                completion_rate = (
                    round((tv_completed / total_started) * 100, 1)
                    if total_started > 0
                    else 54.5
                )
                total_days = total_mins // (60 * 24)

                if self.lang == "en":
                    text = (
                        f"💡 Media Insight: Completion Rate\n\n"
                        f"📊 Out of {total_started} shows started:\n"
                        f"✅ {tv_completed} are 100% completed ({completion_rate}% completion rate).\n\n"
                        f"⏳ {total_mins:,} mins equal {total_days} continuous days of fiction.\n\n"
                        f"#Statistics #TVShows {self.tracker_tag}"
                    )
                elif self.lang == "ca":
                    text = (
                        f"💡 Curiositat Serèfila: Finalització\n\n"
                        f"📊 De {total_started} sèries començades:\n"
                        f"✅ {tv_completed} estan acabades al 100% ({completion_rate}% de fidelitat).\n\n"
                        f"⏳ Els {total_mins:,} mins equivalen a {total_days} dies continus de ficció.\n\n"
                        f"#Estadístiques #Series {self.tracker_tag}"
                    )
                else:
                    text = (
                        f"💡 Curiosidad Seriéfila: Finalización\n\n"
                        f"📊 De {total_started} series empezadas:\n"
                        f"✅ {tv_completed} están terminadas al 100% ({completion_rate}% de fidelidad).\n\n"
                        f"⏳ Los {total_mins:,} mins equivalen a {total_days} días continuos de ficción.\n\n"
                        f"#Estadísticas #Series {self.tracker_tag}"
                    )

            if text and self.bsky.post_watch(text=text):
                log.info("Publicado Fun Fact para %s con éxito.", fact_marker)
                self.storage.set_last_stats_posted("fun_fact", fact_marker)

        except Exception as e:
            log.error("Error al generar Fun Fact: %s", e, exc_info=True)
