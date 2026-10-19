import json
import logging
import threading
import time
from pathlib import Path

logger = logging.getLogger("Mai.UserProfiles")

_PROFILES_DIR = Path(__file__).resolve().parent / "profiles"
_profiles_lock = threading.RLock()


def _ensure_dir():
    _PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def _path(name: str) -> Path:
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
    return _PROFILES_DIR / f"{safe}.json"


def get_profile(name: str) -> dict:
    _ensure_dir()
    path = _path(name)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("get_profile(%s) failed: %s", name, exc)
    return _default_profile(name)


def _default_profile(name: str) -> dict:
    return {
        "name": name,
        "first_seen": time.time(),
        "last_interaction": time.time(),
        "interaction_count": 0,
        "known_facts": [],
        "preferences": {"likes": [], "dislikes": []},
    }


def update_profile(name: str, **kwargs) -> dict:
    with _profiles_lock:
        _ensure_dir()
        profile = get_profile(name)
        profile.update(kwargs)
        profile["last_interaction"] = time.time()
        profile["interaction_count"] = profile.get("interaction_count", 0) + 1
        try:
            path = _path(name)
            path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("update_profile(%s) failed: %s", name, exc)
        return profile


def add_fact(name: str, fact: str) -> dict:
    with _profiles_lock:
        profile = get_profile(name)
        facts = profile.setdefault("known_facts", [])
        if fact not in facts:
            facts.append(fact)
        return update_profile(name, known_facts=facts)


def add_preference(name: str, category: str, item: str) -> dict:
    with _profiles_lock:
        profile = get_profile(name)
        prefs = profile.setdefault("preferences", {"likes": [], "dislikes": []})
        prefs.setdefault(category, [])
        if item not in prefs[category]:
            prefs[category].append(item)
        return update_profile(name, preferences=prefs)


def list_profiles() -> list[str]:
    _ensure_dir()
    return sorted(
        p.stem for p in _PROFILES_DIR.glob("*.json")
    )


def delete_profile(name: str) -> bool:
    with _profiles_lock:
        path = _path(name)
        if path.exists():
            try:
                path.unlink()
                return True
            except Exception as exc:
                logger.warning("delete_profile(%s) failed: %s", name, exc)
        return False


def all_profiles_data() -> list[dict]:
    return [get_profile(name) for name in list_profiles()]
