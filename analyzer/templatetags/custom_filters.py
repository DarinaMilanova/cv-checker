from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Template filter to get dictionary[key] safely."""
    if isinstance(dictionary, dict):
        return dictionary.get(key, "")
    return ""

_FRIENDLY = {
    "Api_Technologies": "API & Web",
    "Ci_Cd_Tooling": "CI/CD Tooling",
    "Qa_Testing": "QA & Testing",
    "Cloud_Platforms": "Cloud Platforms",
    "Infrastructure_As_Code": "Infrastructure as Code",
    "Programming_Languages": "Programming Languages",
    "Frameworks_Libraries": "Frameworks & Libraries",
    "Mobile_Crossplatform": "Mobile (Cross-platform)",
    "Ui_Ux": "UI/UX",
    "Databases_Caches": "Databases & Caches",
    "Observability": "Observability",
}

@register.filter
def display_cat(raw: str) -> str:
    """Turn raw taxonomy keys into user-friendly labels."""
    if not raw:
        return ""
    return _FRIENDLY.get(raw, raw.replace("_", " ").replace("-", " ").title())
