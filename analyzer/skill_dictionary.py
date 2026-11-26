"""Skill dictionary management and dynamic loading.

Manages loading, organizing, validating, and updating skills and categories
from structured JSON files with deduplication and error handling.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Terms that are common English words or letters requiring contextual matching
AMBIGUOUS_TERMS = {
    "c", "r", "go", "node", "express", "swift", "oracle", "excel",
}

# Framework names preventing the alias "js" from incorrectly matching
JS_FRAMEWORK_WORDS = ["node", "react", "vue", "express", "next", "angular"]

_SPACE = r"[^\S\n]"

_BEFORE_AMBIGUOUS = (
    r"(?:^|[,;:|/•·●▪*(\[–-]|\b(?:in|of|with|using|and|or)\b|&)"
    + _SPACE + r"*"
)
_AFTER_AMBIGUOUS = (
    r"(?=" + _SPACE + r"*(?:$|[,;:|/•·●▪)\]]|\.(?:\s|$))"
    r"|" + _SPACE + r"+(?:and|or|&)" + _SPACE + r")"
)


def _term_to_regex(term: str) -> str:
    """Turn a skill name or alias into a regex pattern."""
    parts = re.split(r"[\s-]+", term.lower().strip())
    return r"[\s\-]+".join(re.escape(part) for part in parts)


def _compile_term(term: str) -> re.Pattern:
    """Build the compiled regex for a single skill name or alias."""
    body = _term_to_regex(term)

    if term.lower() in AMBIGUOUS_TERMS:
        return re.compile(
            _BEFORE_AMBIGUOUS + body + _AFTER_AMBIGUOUS,
            re.IGNORECASE | re.MULTILINE,
        )

    if term.lower() == "js":
        blockers = "".join(rf"(?<!{word}\s)" for word in JS_FRAMEWORK_WORDS)
        body = blockers + body

    return re.compile(r"(?<![\w.])" + body + r"(?!\w)", re.IGNORECASE)


def compile_skill_patterns(categories: Dict[str, Dict[str, List[str]]]) -> List[Tuple[str, List[re.Pattern]]]:
    """Compile search patterns for all canonical skills and their aliases."""
    patterns = []
    for _group_name, group in categories.items():
        if isinstance(group, dict):
            for skill, aliases in group.items():
                terms = [skill] + (aliases if isinstance(aliases, list) else [])
                compiled = [_compile_term(t) for t in terms if t and str(t).strip()]
                if compiled:
                    patterns.append((skill, compiled))
    return patterns


def get_default_dictionary_path() -> str:
    """Resolve the default skills dictionary file path."""
    env_path = os.environ.get("SKILLS_DICTIONARY_PATH")
    if env_path:
        return env_path

    # Root project path: <project_root>/data/skills_dictionary.json
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    primary = os.path.join(root_dir, "data", "skills_dictionary.json")
    if os.path.exists(primary):
        return primary

    # Secondary location inside analyzer module directory
    secondary = os.path.join(os.path.dirname(__file__), "skills_dictionary.json")
    if os.path.exists(secondary):
        return secondary

    return primary


def normalize_skill_dictionary(raw_data: Any) -> Dict[str, Dict[str, List[str]]]:
    """Normalize and deduplicate raw dictionary data into structured categories.

    Ensures:
    1. Categories and canonical skill names are organized cleanly.
    2. Alternative skill names (aliases) are preserved as lists.
    3. Duplicate canonical entries (case-insensitive) are avoided.
    4. Duplicate aliases for a skill are pruned.
    5. Aliases matching the canonical name are omitted.
    6. Aliases already claimed by another skill are prevented from colliding.
    """
    if not isinstance(raw_data, dict):
        return {}

    # Handle wrapped structures like {"categories": {...}}
    source_categories = raw_data.get("categories", raw_data)
    if not isinstance(source_categories, dict):
        return {}

    normalized: Dict[str, Dict[str, List[str]]] = {}
    registered_canonical: Dict[str, str] = {}  # lower_canonical -> registered_canonical
    claimed_aliases: Dict[str, str] = {}       # lower_term -> owner_skill

    for cat_name, skills_data in source_categories.items():
        cleaned_cat = str(cat_name).strip()
        if not cleaned_cat:
            continue

        if cleaned_cat not in normalized:
            normalized[cleaned_cat] = {}

        # Format A: {"SkillName": ["alias1", "alias2"]}
        if isinstance(skills_data, dict):
            for skill_name, aliases in skills_data.items():
                canonical = str(skill_name).strip()
                if not canonical:
                    continue

                canonical_lower = canonical.lower()

                # Deduplicate canonical names across categories
                if canonical_lower in registered_canonical:
                    target_skill = registered_canonical[canonical_lower]
                else:
                    registered_canonical[canonical_lower] = canonical
                    target_skill = canonical
                    normalized[cleaned_cat][canonical] = []
                    claimed_aliases[canonical_lower] = canonical

                # Find the owner category & skill to append any new aliases
                dest_list = None
                for c_dict in normalized.values():
                    if target_skill in c_dict:
                        dest_list = c_dict[target_skill]
                        break

                if dest_list is None:
                    dest_list = normalized[cleaned_cat].setdefault(target_skill, [])

                # Process aliases
                raw_aliases = aliases if isinstance(aliases, (list, tuple, set)) else ([aliases] if aliases else [])
                for alias in raw_aliases:
                    if not alias:
                        continue
                    alias_clean = str(alias).strip()
                    if not alias_clean:
                        continue
                    alias_lower = alias_clean.lower()

                    # Avoid alias matching canonical name
                    if alias_lower == canonical_lower:
                        continue

                    # Avoid duplicate alias within this skill
                    if any(a.lower() == alias_lower for a in dest_list):
                        continue

                    # Avoid collision if alias already claimed by another skill
                    if alias_lower in claimed_aliases and claimed_aliases[alias_lower] != target_skill:
                        logger.debug(
                            "Alias %r already claimed by %s; skipping for %s",
                            alias_clean, claimed_aliases[alias_lower], target_skill
                        )
                        continue

                    dest_list.append(alias_clean)
                    claimed_aliases[alias_lower] = target_skill

        # Format B: ["SkillA", {"name": "SkillB", "aliases": [...]}]
        elif isinstance(skills_data, (list, tuple)):
            for item in skills_data:
                if isinstance(item, str):
                    item_name = item.strip()
                    item_aliases = []
                elif isinstance(item, dict):
                    item_name = str(item.get("name", "")).strip()
                    item_aliases = item.get("aliases", [])
                else:
                    continue

                if not item_name:
                    continue

                canonical_lower = item_name.lower()
                if canonical_lower in registered_canonical:
                    continue

                registered_canonical[canonical_lower] = item_name
                claimed_aliases[canonical_lower] = item_name
                clean_aliases = []
                for a in item_aliases:
                    if a and str(a).strip():
                        a_clean = str(a).strip()
                        a_lower = a_clean.lower()
                        if a_lower != canonical_lower and a_lower not in claimed_aliases:
                            clean_aliases.append(a_clean)
                            claimed_aliases[a_lower] = item_name

                normalized[cleaned_cat][item_name] = clean_aliases

    # Clean out empty categories
    return {cat: skills for cat, skills in normalized.items() if skills}


def load_skills_dictionary(
    filepath: Optional[str] = None,
    fallback: Optional[Dict[str, Dict[str, List[str]]]] = None
) -> Dict[str, Dict[str, List[str]]]:
    """Load and normalize skill categories from a JSON file safely.

    Handles missing files, unreadable files, and malformed JSON by falling back
    to the provided fallback dictionary without throwing uncaught exceptions.
    """
    target_path = filepath or get_default_dictionary_path()

    if not os.path.exists(target_path):
        logger.warning("Skills dictionary file not found: %s. Using fallback.", target_path)
        return normalize_skill_dictionary(fallback) if fallback else {}

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as err:
        logger.error("Failed to load skills dictionary from %s (%s). Using fallback.", target_path, err)
        return normalize_skill_dictionary(fallback) if fallback else {}

    normalized = normalize_skill_dictionary(raw_data)
    if not normalized and fallback:
        logger.warning("Loaded dictionary from %s was empty. Using fallback.", target_path)
        return normalize_skill_dictionary(fallback)

    return normalized


def save_skills_dictionary(
    categories: Dict[str, Dict[str, List[str]]],
    filepath: Optional[str] = None
) -> bool:
    """Save normalized skill categories into a structured JSON file."""
    target_path = filepath or get_default_dictionary_path()
    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(categories, f, indent=2, ensure_ascii=False)
        return True
    except OSError as err:
        logger.error("Failed to save skills dictionary to %s: %s", target_path, err)
        return False


def get_all_skills_flat(categories: Dict[str, Dict[str, List[str]]]) -> List[str]:
    """Return flat list of all canonical skills in the order defined."""
    return [
        skill
        for group in categories.values()
        for skill in group
    ]


class SkillDictionaryManager:
    """Manages skill dictionary state with dynamic loading and caching."""

    def __init__(
        self,
        filepath: Optional[str] = None,
        fallback: Optional[Dict[str, Dict[str, List[str]]]] = None,
        categories: Optional[Dict[str, Dict[str, List[str]]]] = None,
        auto_reload: bool = True
    ):
        self.filepath = filepath
        self.fallback = fallback or {}
        self.auto_reload = auto_reload

        self._cached_categories: Optional[Dict[str, Dict[str, List[str]]]] = None
        self._cached_skills: Optional[List[str]] = None
        self._cached_patterns: Optional[List[Tuple[str, List[re.Pattern]]]] = None
        self._last_mtime: Optional[float] = None

        if categories is not None:
            self._cached_categories = normalize_skill_dictionary(categories)
            self._cached_skills = get_all_skills_flat(self._cached_categories)
            self._cached_patterns = compile_skill_patterns(self._cached_categories)
        elif self.filepath is None and self.fallback:
            self._cached_categories = normalize_skill_dictionary(self.fallback)
            self._cached_skills = get_all_skills_flat(self._cached_categories)
            self._cached_patterns = compile_skill_patterns(self._cached_categories)
        else:
            if self.filepath is None:
                self.filepath = get_default_dictionary_path()
            self.reload()

    def _has_file_changed(self) -> bool:
        """Check if the underlying dictionary file was modified."""
        if not self.filepath or not os.path.exists(self.filepath):
            return self._last_mtime is not None
        try:
            current_mtime = os.path.getmtime(self.filepath)
            return current_mtime != self._last_mtime
        except OSError:
            return False

    def reload(self) -> None:
        """Force a reload of the dictionary from disk."""
        self._cached_categories = load_skills_dictionary(self.filepath, fallback=self.fallback)
        self._cached_skills = get_all_skills_flat(self._cached_categories)
        self._cached_patterns = compile_skill_patterns(self._cached_categories)

        if os.path.exists(self.filepath):
            try:
                self._last_mtime = os.path.getmtime(self.filepath)
            except OSError:
                self._last_mtime = None
        else:
            self._last_mtime = None

    def get_categories(self, force_reload: bool = False) -> Dict[str, Dict[str, List[str]]]:
        """Get the current category dictionary, checking for dynamic file updates."""
        if force_reload or (self.auto_reload and self._has_file_changed()):
            self.reload()
        return self._cached_categories or {}

    def get_skills(self, force_reload: bool = False) -> List[str]:
        """Get flat list of canonical skill names."""
        if force_reload or (self.auto_reload and self._has_file_changed()):
            self.reload()
        return self._cached_skills or []

    def get_patterns(self, force_reload: bool = False) -> List[Tuple[str, List[re.Pattern]]]:
        """Get compiled regex patterns."""
        if force_reload or (self.auto_reload and self._has_file_changed()):
            self.reload()
        return self._cached_patterns or []

    def extract_skills(
        self,
        resume_text: Optional[str],
        custom_dictionary: Optional[Any] = None
    ) -> List[str]:
        """Extract skills from text dynamically.

        If a custom dictionary (dict or filepath) is provided, it is dynamically
        normalized and compiled for this extraction.
        """
        text = resume_text or ""
        if not text.strip():
            return []

        # If custom dictionary provided, compile dynamically
        if custom_dictionary:
            if isinstance(custom_dictionary, str):
                categories = load_skills_dictionary(custom_dictionary, fallback=self.get_categories())
            else:
                categories = normalize_skill_dictionary(custom_dictionary)
            patterns = compile_skill_patterns(categories)
        else:
            patterns = self.get_patterns()

        found_skills = []
        for skill, skill_patterns in patterns:
            if any(pattern.search(text) for pattern in skill_patterns):
                found_skills.append(skill)

        return found_skills

    def add_skill(
        self,
        category: str,
        skill_name: str,
        aliases: Optional[List[str]] = None,
        save: bool = False
    ) -> bool:
        """Add a skill to a category, avoiding duplicate entries."""
        categories = self.get_categories()
        clean_cat = str(category).strip()
        clean_skill = str(skill_name).strip()

        if not clean_cat or not clean_skill:
            return False

        # Build raw dict to re-normalize
        if clean_cat not in categories:
            categories[clean_cat] = {}

        existing_aliases = categories[clean_cat].get(clean_skill, [])
        new_aliases = list(existing_aliases)
        if aliases:
            new_aliases.extend(aliases)

        categories[clean_cat][clean_skill] = new_aliases
        normalized = normalize_skill_dictionary(categories)

        self._cached_categories = normalized
        self._cached_skills = get_all_skills_flat(normalized)
        self._cached_patterns = compile_skill_patterns(normalized)

        if save:
            return save_skills_dictionary(normalized, self.filepath)
        return True
