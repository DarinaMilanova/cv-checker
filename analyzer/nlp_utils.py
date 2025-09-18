# analyzer/nlp_utils.py
import re
import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

BASE_DIR = Path(__file__).resolve().parent.parent / "config"
TAXONOMY_PATH = BASE_DIR / "skills_taxonomy.json"
LEVEL_SIGNALS_PATH = BASE_DIR / "level_signals.json"

def normalize_word(text: str) -> str:
    return unicodedata.normalize("NFKC", (text or "").strip().lower())

def _load_json(path: Path, default):
    try:
        if not path.exists():
            return default
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default

_raw_taxonomy = _load_json(TAXONOMY_PATH, {})
_level_signals = _load_json(LEVEL_SIGNALS_PATH, {})

CATEGORY_SKILLS: dict[str, set[str]] = {}
ALIAS_LOOKUP: dict[str, str] = {}
SKILL_TO_CATEGORY: dict[str, str] = {}

for cat_name, entry_map in (_raw_taxonomy or {}).items():
    cat_norm = normalize_word(cat_name)
    CATEGORY_SKILLS[cat_norm] = set()

    skills_list = (entry_map or {}).get("skills", []) or []
    aliases_map = (entry_map or {}).get("aliases", {}) or {}


    for canon_name in skills_list:
        canon_norm = normalize_word(canon_name)
        if not canon_norm:
            continue
        CATEGORY_SKILLS[cat_norm].add(canon_norm)
        SKILL_TO_CATEGORY[canon_norm] = cat_norm
        ALIAS_LOOKUP[canon_norm] = canon_norm

    for alias_name, target in aliases_map.items():
        alias_norm = normalize_word(alias_name)
        target_norm = normalize_word(target)
        if alias_norm and target_norm and target_norm in SKILL_TO_CATEGORY:
            ALIAS_LOOKUP[alias_norm] = target_norm

NOISE_TERMS = {
    "experience","years","year","education","degree","bachelor","master","phd",
    "responsibilities","requirements","skills","technologies","stack","tools",
    "benefits","perks","culture","opportunity","position","role","candidate",
    "company","environment","team","work","working","projects","project",
    "preferred","required","knowledge","familiarity","understanding",
    "junior","senior","entry","mid","expert"
}

def _split_connectors(s: str) -> list[str]:
    return re.split(r"[ \t_/-]+", s)

def _build_phrase_patterns(alias_lookup: dict[str, str]):
    items: list[tuple[re.Pattern[str], str]] = []
    pairs = sorted(alias_lookup.items(), key=lambda kv: len(kv[0]), reverse=True)
    for alias_val, canon_val in pairs:
        if any(ch in alias_val for ch in (" ", "-", "_", "/", ".")):
            parts = [re.escape(p) for p in _split_connectors(alias_val) if p]
            if not parts:
                continue
            connector = r"[ \t_/.\-]+"
            pat = re.compile(r"\b" + connector.join(parts) + r"\b", flags=re.IGNORECASE)
            placeholder = "__" + canon_val.replace(" ", "_") + "__"
            items.append((pat, placeholder))
    return items

_PHRASE_PATTERNS = _build_phrase_patterns(ALIAS_LOOKUP)

def _apply_phrase_placeholders(text: str) -> str:
    new_text = text
    for pattern, placeholder in _PHRASE_PATTERNS:
        new_text = pattern.sub(placeholder, new_text)
    return new_text

def _extract_placeholders(text: str) -> list[str]:
    return re.findall(r"__([a-z0-9_]+)__", text)

def _canonicalize_token(token: str) -> str | None:
    token = re.sub(r'[.,;:!?)\]"\'”’}>]+$', '', token or "")
    t = normalize_word(token)
    if not t or t in NOISE_TERMS:
        return None
    mapped = ALIAS_LOOKUP.get(t)
    if mapped:
        return mapped
    short_whitelist = {"go","r","c","c#","c++"}
    if (len(t) < 3 and t not in short_whitelist) or t.isdigit():
        return None
    if t in SKILL_TO_CATEGORY:
        return t
    return None

_TOKEN_RE = re.compile(r"[a-z0-9#+.]+", flags=re.IGNORECASE)

def tokenize_and_normalize(text: str, lang: str | None = None) -> tuple[list[str], str]:
    if not text:
        return [], (lang or "en")
    if not lang:
        try:
            lang = detect(text) or "en"
        except LangDetectException:
            lang = "en"
    replaced = _apply_phrase_placeholders(text)
    tokens_list: list[str] = []
    for ph in _extract_placeholders(replaced):
        ph_norm = ph.replace("_", " ")
        canonical = ALIAS_LOOKUP.get(ph_norm, ph_norm)
        if canonical in SKILL_TO_CATEGORY:
            tokens_list.append(canonical)
    for raw_tok in _TOKEN_RE.findall(replaced):
        if raw_tok.startswith("__") and raw_tok.endswith("__"):
            continue
        canonical = _canonicalize_token(raw_tok)
        if canonical:
            tokens_list.append(canonical)
    return tokens_list, lang

def extract_keywords(text: str, top_n: int = 20, lang: str | None = None) -> list[str]:
    tokens_list, _ = tokenize_and_normalize(text, lang)
    tokens_list = [t for t in tokens_list if t in SKILL_TO_CATEGORY]
    return [kw for kw, _ in Counter(tokens_list).most_common(top_n)]

def extract_all_keywords(text: str, lang: str | None = None) -> tuple[list[str], list[tuple[str, int]]]:
    tokens_list, _ = tokenize_and_normalize(text or "", lang)
    tokens_list = [t for t in tokens_list if t in SKILL_TO_CATEGORY]
    counts = Counter(tokens_list)
    ordered = counts.most_common()
    full_list = [k for k, _ in ordered]
    return full_list, ordered

def map_tokens_to_categories(tokens: list[str]) -> dict[str, set[str]]:
    categorized: dict[str, set[str]] = defaultdict(set)
    for tok in tokens:
        cat = SKILL_TO_CATEGORY.get(tok)
        if cat:
            categorized[cat].add(tok)
    return categorized

_LEVEL_KEY_MAP = {"entry": "entry","junior": "entry","mid": "mid","mid-level": "mid",
                  "intermediate": "mid","regular": "mid","professional": "mid",
                  "senior": "senior","sr": "senior","expert": "expert",
                  "principal": "expert","architect": "expert"}

def _norm_level_key(k: str) -> str:
    k_norm = normalize_word(k)
    if k_norm in ("entry","mid","senior","expert"):
        return k_norm
    return _LEVEL_KEY_MAP.get(k_norm, k_norm)

def detect_seniority(text: str) -> dict:
    doc = normalize_word(text or "")
    scores = {"entry": 0, "mid": 0, "senior": 0, "expert": 0}
    for level_key, payload in (_level_signals or {}).items():
        level_norm = _norm_level_key(level_key)
        if level_norm not in scores: continue
        for phrase in (payload or {}).get("phrases", []):
            if normalize_word(phrase) and re.search(r"\b"+re.escape(phrase)+r"\b", doc):
                scores[level_norm] += 1
        for rx in (payload or {}).get("regex", []):
            try:
                scores[level_norm] += len(re.compile(rx, re.I).findall(doc))
            except re.error: continue
    predicted = max(scores, key=scores.get) if scores else "mid"
    return {**scores, "predicted": predicted}

def compare_skills_by_category(cv_text: str, jd_text: str):
    cv_tokens, _ = tokenize_and_normalize(cv_text or "")
    jd_tokens, _ = tokenize_and_normalize(jd_text or "")
    cv_categories = map_tokens_to_categories(cv_tokens)
    jd_categories = map_tokens_to_categories(jd_tokens)
    matched, missing, extra, category_scores = {}, {}, {}, {}
    for cat_key, jd_sk in jd_categories.items():
        cv_sk = cv_categories.get(cat_key, set())
        matched[cat_key] = sorted(cv_sk & jd_sk)
        missing[cat_key] = sorted(jd_sk - cv_sk)
        total = len(jd_sk) or 1
        category_scores[cat_key] = round(len(matched[cat_key]) / total * 100.0, 2)
    for cat_key, cv_sk in cv_categories.items():
        jd_sk = jd_categories.get(cat_key, set())
        extra[cat_key] = sorted(cv_sk - jd_sk)
    return matched, missing, extra, category_scores, cv_tokens, jd_tokens

def get_result_text(match_percent: float) -> str:
    if match_percent >= 90: return "Excellent match — strong overlap across core skills."
    if match_percent >= 70: return "Good match — solid overlap with a few areas to improve."
    if match_percent >= 50: return "Partial match — several gaps to address for a better fit."
    return "Low alignment — consider tailoring your CV toward the role."

def build_recommendations(missing_keywords: list[str], top_n: int = 5) -> list[str]:
    return [f"Add or highlight experience with {kw}." for kw in missing_keywords[:top_n]]

def analyze_texts(cv_text: str, jd_text: str):
    cv_keywords = extract_keywords(cv_text or "")
    jd_keywords = extract_keywords(jd_text or "")
    cv_keywords_full, cv_keyword_counts = extract_all_keywords(cv_text or "")
    jd_keywords_full, jd_keyword_counts = extract_all_keywords(jd_text or "")
    matched, missing, extra, category_scores, cv_tokens, jd_tokens = compare_skills_by_category(cv_text or "", jd_text or "")
    overall = round(sum(category_scores.values()) / (len(category_scores) or 1), 2)
    jd_level = detect_seniority(jd_text or "")
    cv_level = detect_seniority(cv_text or "")
    matched_keywords = sorted({sk for v in matched.values() for sk in v})
    missing_keywords = sorted({sk for v in missing.values() for sk in v})
    extra_keywords = sorted(set(cv_tokens) - set(jd_tokens))
    return {
        "cv_keywords": cv_keywords,
        "jd_keywords": jd_keywords,
        "cv_keywords_full": cv_keywords_full,
        "jd_keywords_full": jd_keywords_full,
        "cv_keyword_counts": cv_keyword_counts,
        "jd_keyword_counts": jd_keyword_counts,
        "matched_by_category": matched,
        "missing_by_category": missing,
        "extra_by_category": extra,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "extra_keywords": extra_keywords,
        "category_scores": category_scores,
        "match_percent": overall,
        "overall": overall,  # alias
        "ai_result_text": get_result_text(overall),
        "jd_level": jd_level,
        "jd_level_signals": [],
        "cv_level": cv_level,
        "recommendations": build_recommendations(missing_keywords),
        "evidence": {},
    }