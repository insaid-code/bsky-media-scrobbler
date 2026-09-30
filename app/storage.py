import json
import logging
import os
from datetime import date, datetime, timezone

log = logging.getLogger("simkl-bluesky")

DEFAULT_STATE_FILE = os.getenv("STATE_FILE", "/data/state.json")
EPOCH_ISO = "1970-01-01T00:00:00Z"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Storage:
    def __init__(self, file_path: str = DEFAULT_STATE_FILE):
        self.file_path = file_path
        self._ensure_dir()
        self.data = self._load()

    def _ensure_dir(self):
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception as e:
                log.warning("No se pudo crear el directorio de datos %s: %s", directory, e)

    def _load(self) -> dict:
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        # Asegurar claves mínimas
                        data.setdefault("history_seeded", False)
                        data.setdefault("simkl_token", None)
                        data.setdefault("last_checked", {
                            "shows": EPOCH_ISO,
                            "anime": EPOCH_ISO,
                            "movies": EPOCH_ISO,
                        })
                        data.setdefault("announced", [])
                        data.setdefault("recent_phrases", [])
                        data.setdefault("last_stats_posted", {})
                        data.setdefault("celebrated_milestones", [])
                        data.setdefault("streak_data", {
                            "current_streak": 0,
                            "last_active_date": "",
                            "max_streak": 0,
                            "celebrated_streaks": [],
                        })
                        return data
            except Exception as e:
                log.error("Error al cargar %s: %s. Creando estado inicial.", self.file_path, e)

        return {
            "history_seeded": False,
            "simkl_token": None,
            "last_checked": {
                "shows": EPOCH_ISO,
                "anime": EPOCH_ISO,
                "movies": EPOCH_ISO,
            },
            "announced": [],
            "recent_phrases": [],
            "last_stats_posted": {},
            "celebrated_milestones": [],
            "streak_data": {
                "current_streak": 0,
                "last_active_date": "",
                "max_streak": 0,
                "celebrated_streaks": [],
            },
        }

    def save(self):
        try:
            temp_path = f"{self.file_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.file_path)
        except Exception as e:
            log.error("Error al guardar el estado en %s: %s", self.file_path, e)

    def is_seeded(self) -> bool:
        return bool(self.data.get("history_seeded"))

    def mark_seeded(self, announced_keys: list[str]):
        self.data["history_seeded"] = True
        current_announced = set(self.data.get("announced", []))
        current_announced.update(announced_keys)
        self.data["announced"] = list(current_announced)
        # Fijar last_checked a ahora mismo para no revisar hacia atrás
        current_time = now_iso()
        self.data["last_checked"] = {
            "shows": current_time,
            "anime": current_time,
            "movies": current_time,
        }
        self.save()

    def get_announced(self) -> set[str]:
        return set(self.data.get("announced", []))

    def add_announced(self, keys: list[str]):
        current = set(self.data.get("announced", []))
        current.update(keys)
        # Limitar historial de anunciados si crece demasiado (ej. conservar últimos 10.000)
        if len(current) > 15000:
            current = set(list(current)[-10000:])
        self.data["announced"] = list(current)
        self.save()

    def get_last_checked(self, media_type: str) -> str:
        return self.data.get("last_checked", {}).get(media_type, EPOCH_ISO)

    def set_last_checked(self, media_type: str, timestamp_iso: str):
        if "last_checked" not in self.data:
            self.data["last_checked"] = {}
        self.data["last_checked"][media_type] = timestamp_iso
        self.save()

    def get_token(self) -> str | None:
        return self.data.get("simkl_token")

    def set_token(self, token: str):
        self.data["simkl_token"] = token
        self.save()

    def get_wetrakr_token(self) -> dict | None:
        return self.data.get("wetrakr_token")

    def set_wetrakr_token(self, token_data: dict | str):
        if isinstance(token_data, str):
            token_data = {"access_token": token_data}
        self.data["wetrakr_token"] = token_data
        self.save()

    def get_recent_phrases(self) -> list[str]:
        return self.data.get("recent_phrases", [])

    def add_recent_phrase(self, phrase_prefix: str, max_history: int = 15):
        current = self.data.get("recent_phrases", [])
        current.append(phrase_prefix)
        if len(current) > max_history:
            current = current[-max_history:]
        self.data["recent_phrases"] = current
        self.save()

    def get_last_stats_posted(self, category: str) -> str | None:
        return self.data.get("last_stats_posted", {}).get(category)

    def set_last_stats_posted(self, category: str, marker: str):
        if "last_stats_posted" not in self.data:
            self.data["last_stats_posted"] = {}
        self.data["last_stats_posted"][category] = marker
        self.save()

    def get_celebrated_milestones(self) -> list[str]:
        return self.data.get("celebrated_milestones", [])

    def add_celebrated_milestone(self, milestone_id: str):
        milestones = self.data.get("celebrated_milestones", [])
        if milestone_id not in milestones:
            milestones.append(milestone_id)
            self.data["celebrated_milestones"] = milestones
            self.save()

    def get_streak_info(self) -> dict:
        return self.data.get("streak_data", {
            "current_streak": 0,
            "last_active_date": "",
            "max_streak": 0,
            "celebrated_streaks": [],
        })

    def record_activity_date(self, date_str: str) -> tuple[int, bool]:
        """
        Registra un día con actividad de visionado ("YYYY-MM-DD") y actualiza la racha.
        Devuelve (racha_actual, es_nuevo_hito_a_celebrar).
        """
        if "streak_data" not in self.data:
            self.data["streak_data"] = {
                "current_streak": 0,
                "last_active_date": "",
                "max_streak": 0,
                "celebrated_streaks": [],
            }
        sdata = self.data["streak_data"]
        try:
            today = date.fromisoformat(date_str)
        except Exception:
            return sdata.get("current_streak", 0), False

        last_str = sdata.get("last_active_date")
        if not last_str:
            sdata["current_streak"] = 1
            sdata["last_active_date"] = date_str
            sdata["max_streak"] = max(sdata.get("max_streak", 0), 1)
        else:
            try:
                last_date = date.fromisoformat(last_str)
                delta = (today - last_date).days
                if delta == 0:
                    pass  # Ya contabilizado hoy
                elif delta == 1:
                    sdata["current_streak"] = sdata.get("current_streak", 0) + 1
                    sdata["last_active_date"] = date_str
                    sdata["max_streak"] = max(sdata.get("max_streak", 0), sdata["current_streak"])
                elif delta > 1:
                    sdata["current_streak"] = 1
                    sdata["last_active_date"] = date_str
            except Exception:
                sdata["current_streak"] = 1
                sdata["last_active_date"] = date_str

        current_streak = sdata["current_streak"]
        celebrated = set(sdata.get("celebrated_streaks", []))
        milestones = [7, 14, 30, 50, 100, 150, 200, 300, 365, 500, 750, 1000]

        is_new_milestone = False
        if current_streak in milestones and current_streak not in celebrated:
            is_new_milestone = True
            celebrated.add(current_streak)
            sdata["celebrated_streaks"] = list(celebrated)

        self.save()
        return current_streak, is_new_milestone

