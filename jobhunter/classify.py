"""규칙 기반 공고 분류 + 적합도 점수(0~100)."""
from __future__ import annotations
import re
from .profile import PROFILE_KEYWORDS, NEGATIVE_KEYWORDS

_MAX_RAW = 60  # 이 점수 이상이면 만점 (상위 공고끼리도 순위가 갈리도록)


def _count(text: str, kw: str) -> int:
    if re.fullmatch(r"[a-z0-9+/\-\.]+", kw) and len(kw) <= 3:
        # 짧은 영문 키워드는 단어 경계로 매칭 (예: 'rf'가 'surf'에 걸리지 않도록)
        return len(re.findall(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", text))
    return text.count(kw)


def classify(title: str, description: str = "") -> dict:
    text = f"{title} {title} {description}".lower()  # 제목 가중
    raw = 0
    cats: dict[str, int] = {}
    matched: list[str] = []
    for cat, kws in PROFILE_KEYWORDS.items():
        for kw, w in kws.items():
            c = min(_count(text, kw), 2)  # 반복 매칭 상한
            if c:
                cats[cat] = cats.get(cat, 0) + w * c
                raw += w * c
                matched.append(kw)
    for kw, w in NEGATIVE_KEYWORDS.items():
        if kw in text:
            raw += w
    score = max(0, min(100, round(raw / _MAX_RAW * 100)))
    categories = sorted(cats, key=cats.get, reverse=True)
    return {"score": score, "categories": categories, "matched": sorted(set(matched))}
