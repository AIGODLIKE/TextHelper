"""Cross-language font search aliases (brand-specific, conservative)."""

from __future__ import annotations

import unicodedata

# (triggers, extra index/query tokens) — only the matched row expands, never whole-table unions.
_ALIAS_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (
        ("思源", "思源黑体", "思源宋体", "siyuan", "si yuan"),
        (
            "source",
            "source han",
            "source han sans",
            "source han serif",
            "sourcehansans",
            "sourcehanserif",
        ),
    ),
    (
        (
            "source han",
            "source han sans",
            "source han serif",
            "sourcehansans",
            "sourcehanserif",
            "source han sans sc",
            "source han sans tc",
        ),
        ("思源", "思源黑体", "思源宋体", "siyuan"),
    ),
    (
        ("noto sans cjk", "noto sans cjk sc", "noto sans cjk tc", "notosanscjk"),
        ("noto cjk", "noto sans"),
    ),
    (
        ("noto serif cjk", "noto serif cjk sc", "noto serif cjk tc", "notoserifcjk"),
        ("noto cjk serif", "noto serif"),
    ),
    (
        ("微软雅黑", "microsoft yahei", "microsoftyahei", "msyh"),
        ("yahei", "ms yahei"),
    ),
    (
        ("yahei", "ms yahei", "msyh"),
        ("微软雅黑", "microsoft yahei"),
    ),
    (
        ("苹方", "pingfang sc", "pingfangsc", "pingfang"),
        ("ping fang",),
    ),
    (
        ("pingfang", "ping fang", "pingfangsc"),
        ("苹方",),
    ),
    (
        ("冬青黑体", "hiragino sans", "hiragino"),
        ("hiyou", "冬青"),
    ),
    (
        ("hiragino", "hiragino sans"),
        ("冬青黑体", "冬青"),
    ),
)

_QUERY_ONLY_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("source",), ("思源", "siyuan", "source han", "source han sans")),
)

# Generic style words — too broad to use as alias triggers (would match most CJK fonts).
_BLOCKED_TRIGGERS = frozenset(
    {
        "黑体",
        "宋体",
        "楷体",
        "仿宋",
        "华文",
        "兰亭",
        "sans",
        "serif",
        "regular",
        "bold",
        "light",
        "medium",
    }
)


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").strip().lower()


def _has_cjk(text: str) -> bool:
    for char in text:
        code = ord(char)
        if 0x3040 <= code <= 0x30FF or 0x3400 <= code <= 0x4DBF or 0x4E00 <= code <= 0x9FFF or 0xAC00 <= code <= 0xD7AF:
            return True
    return False


def _collect_tokens(*texts: str) -> tuple[str, set[str]]:
    parts = [text for text in texts if text]
    haystack = _normalize(" ".join(parts))
    tokens: set[str] = set()
    for text in parts:
        norm = _normalize(text)
        if norm:
            tokens.add(norm)
        for piece in norm.replace("_", " ").replace("-", " ").split():
            if piece:
                tokens.add(piece)
    return haystack, tokens


def _latin_term_matches(term: str, haystack: str, tokens: set[str]) -> bool:
    term = term.lower()
    if term in tokens:
        return True
    padded = f" {haystack} "
    return f" {term} " in padded


def _trigger_matches(trigger: str, haystack: str, tokens: set[str]) -> bool:
    trigger = trigger.strip()
    if not trigger or trigger.lower() in _BLOCKED_TRIGGERS:
        return False
    norm = _normalize(trigger)
    if _has_cjk(trigger):
        return norm in haystack
    if len(norm) <= 5:
        return _latin_term_matches(norm, haystack, tokens)
    return norm in haystack


def _extras_for_texts(*texts: str, rules=_ALIAS_RULES) -> tuple[str, ...]:
    haystack, tokens = _collect_tokens(*texts)
    if not haystack:
        return ()

    extras: list[str] = []
    seen: set[str] = set()
    for triggers, additions in rules:
        if not any(_trigger_matches(trigger, haystack, tokens) for trigger in triggers):
            continue
        for term in additions:
            key = term.lower()
            if key in seen:
                continue
            seen.add(key)
            extras.append(term)
    return tuple(extras)


def alias_tokens_for_text(*texts: str) -> tuple[str, ...]:
    """Add cross-language tokens to a font search index (blob side)."""
    return _extras_for_texts(*texts, rules=_ALIAS_RULES)


def alias_tokens_for_query(filter_text: str) -> tuple[str, ...]:
    """Expand a user query with cross-language aliases (query side only)."""
    base = (filter_text or "").strip()
    if not base:
        return ()
    split = [_normalize(token) for token in base.replace(",", " ").split() if token.strip()]
    return _extras_for_texts(base, *split, rules=_ALIAS_RULES + _QUERY_ONLY_RULES)
