# product_picker.py
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import math, re

# ---------- Helpers ----------
def _safe_float(x) -> float:
    if isinstance(x, (int, float)): return float(x)
    if not x: return 0.0
    s = str(x).strip().replace(",", "")
    m = re.search(r"([0-9]+(\.[0-9]+)?)", s)
    return float(m.group(1)) if m else 0.0

def _safe_int(x) -> int:
    if isinstance(x, int): return x
    if not x: return 0
    m = re.search(r"([0-9,]+)", str(x))
    return int(m.group(1).replace(",", "")) if m else 0

def _tokenize(s: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9]+", (s or "").lower())

def _norm_rating(r: float) -> float:
    return max(0.0, min(5.0, r)) / 5.0

def _norm_reviews(n: int) -> float:
    return math.log1p(max(0, n)) / math.log(10000 + 1)

# ---------- Category mapping ----------
CATEGORY_PATTERNS = [
    ("bed", r"\bbed\b|\bplatform\b.*\bbed\b|\bbed frame\b"),
    ("nightstand", r"\bnight\s*stand\b|\bbedside\b"),
    ("dresser", r"\bdresser\b|\bchest\b|\bdrawer\b"),
    ("sofa", r"\bsofa\b|\bcouch\b|\bsectional\b|\bloveseat\b"),
    ("chair", r"\baccent chair\b|\barmchair\b|\bdining chair\b|\boffice chair\b|\bstool\b"),
    ("coffee_table", r"\bcoffee table\b"),
    ("side_table", r"\bside table\b|\bend table\b"),
    ("desk", r"\bdesk\b|\bworkspace\b|\bcomputer desk\b"),
    ("rug", r"\brug\b|\b8x10\b|\b5x7\b|\brunner\b"),
    ("lamp", r"\blamp\b|\bfloor lamp\b|\btable lamp\b"),
    ("ceiling_fan", r"\bceiling fan\b|\bflush mount fan\b"),
    ("shelf", r"\bshelf\b|\bbookshelf\b|\bbookcase\b|\bwall shelf\b"),
    ("media_console", r"\btv stand\b|\bmedia console\b|\bentertainment center\b"),
    ("curtains", r"\bcurtain\b|\bdrape\b"),
    ("mirror", r"\bmirror\b"),
    ("wall_art", r"\bwall art\b|\bposter\b|\bprint\b|\bframed\b"),
    ("plant", r"\bplanter\b|\bfaux plant\b|\bpotted\b"),
]

def infer_category(text: str) -> str:
    t = (text or "").lower()
    for cat, pat in CATEGORY_PATTERNS:
        if re.search(pat, t):
            return cat
    return "other"

# ---------- Data ----------
@dataclass
class Candidate:
    query_idx: int
    query_text: str
    asin: Optional[str]
    title: str
    link: Optional[str]
    link_clean: Optional[str]
    thumbnail: Optional[str]
    rating: float
    reviews: int
    price: float
    bought_last_month: Optional[str]
    delivery: List[str]
    prime: bool
    badges: List[str]
    category: str
    score: float = 0.0

    def to_result(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "link": self.link,
            "link_clean": self.link_clean or self.link,
            "thumbnail": self.thumbnail,
            "rating": self.rating if self.rating else None,
            "reviews": self.reviews if self.reviews else None,
            "bought_last_month": self.bought_last_month,
            "price": f"${self.price:,.2f}" if self.price else None,
            "extracted_price": self.price if self.price else None,
            "delivery": self.delivery or [],
        }

# ---------- Extract ----------
def _extract_candidates(raw: Dict[str, Any], query_text: str, qidx: int) -> List[Candidate]:
    cands: List[Candidate] = []

    # Organic (preferred)
    for it in (raw.get("organic_results") or []):
        title = it.get("title", "")
        cands.append(Candidate(
            query_idx=qidx,
            query_text=query_text,
            asin=it.get("asin"),
            title=title,
            link=it.get("link"),
            link_clean=it.get("link_clean") or it.get("link"),
            thumbnail=it.get("thumbnail"),
            rating=_safe_float(it.get("rating")),
            reviews=_safe_int(it.get("reviews")),
            price=_safe_float(it.get("extracted_price") or it.get("price")),
            bought_last_month=it.get("bought_last_month"),
            delivery=it.get("delivery") or [],
            prime=bool(it.get("prime")),
            badges=it.get("badges") or [],
            category=infer_category(f"{title} {query_text}"),
        ))

    # Sponsored / product_ads (secondary)
    pa = raw.get("product_ads") or {}
    for it in (pa.get("products") or []):
        title = it.get("title", "")
        cands.append(Candidate(
            query_idx=qidx,
            query_text=query_text,
            asin=it.get("asin"),
            title=title,
            link=it.get("link"),
            link_clean=it.get("link_clean") or it.get("link"),
            thumbnail=it.get("thumbnail") or pa.get("image"),
            rating=_safe_float(it.get("rating")),
            reviews=_safe_int(it.get("reviews")),
            price=_safe_float(it.get("extracted_price") or it.get("price")),
            bought_last_month=None,
            delivery=[],
            prime=bool(it.get("prime")),
            badges=["Sponsored"],
            category=infer_category(f"{title} {query_text}"),
        ))

    return [c for c in cands if c.title and (c.link or c.link_clean)]

# ---------- Scoring ----------
def _score_candidate(
    c: Candidate,
    style_tokens: List[str],
    query_tokens: List[str],
    target_price: float,
    notes_tokens: List[str],
    selected_categories_set: set,
) -> float:
    title = c.title.lower()

    # matches
    style_match = 1.0 if any(tok in title for tok in style_tokens) else 0.0
    non_style = [t for t in query_tokens if t not in style_tokens]
    kw_match = 1.0 if all(tok in title for tok in non_style) else 0.0

    # notes
    notes_match = 0.0
    if notes_tokens:
        hits = sum(1 for t in notes_tokens if t in title)
        if hits >= 3: notes_match = 1.0
        elif hits >= 1: notes_match = 0.5

    # category priority
    cat_priority = 1.0 if (c.category in selected_categories_set) else 0.0

    prime_flag = 1.0 if c.prime else 0.0
    deal_flag = 0.5 if any(b.lower() in ("overall pick", "limited time deal") for b in (c.badges or [])) else 0.0

    # penalties
    price_penalty = (c.price - target_price) / max(1.0, target_price) if target_price and c.price > target_price else 0.0
    dl = " ".join(c.delivery or []).lower()
    low_rating_pen = 1.0 if c.rating and c.rating < 3.8 else 0.0
    pre_order_pen = 1.0 if ("pre-order" in dl or "preorder" in dl) else 0.0
    long_ship_pen = 0.5 if any(k in dl for k in ["oct", "nov", "dec", "3 weeks", "next year"]) else 0.0

    # FINAL weighted score
    return (
        4.0 * _norm_rating(c.rating) +          # rating weight
        3.0 * _norm_reviews(c.reviews) +        # reviews weight
        2.0 * style_match +                     # style match weight
        2.0 * kw_match +                        # keyword match weight
        1.0 * prime_flag +                      # Prime boost
        deal_flag +                             # Deal boost (0.5)
        1.0 * notes_match +                     # notes boost
        1.5 * cat_priority -                    # category priority
        1.5 * price_penalty -                   # price penalty
        2.0 * (low_rating_pen + pre_order_pen + long_ship_pen) # risk penalties
    )

# ---------- Main API ----------
def pick_products_with_budget(
    query_results: List[Dict[str, Any]],
    budget: float,
    style: str,
    notes: Optional[str] = None,
    selected_products: Optional[List[str]] = None,
    min_rating: float = 4.0,
    min_reviews: int = 50,
    cap_flex: float = 1.25,
) -> List[Dict[str, Any]]:
    queries = [qr for qr in (query_results or []) if qr.get("success") and qr.get("raw_data")]
    if not queries:
        return []

    N = len(queries)
    per_cap = (budget / N) if (budget and N) else 0.0
    style_tokens = _tokenize(style)
    notes_tokens = _tokenize(notes or "")
    selected_products = selected_products or []
    selected_categories_set = {infer_category(p) for p in selected_products}

    per_query_pools: List[List[Candidate]] = []

    for qidx, qr in enumerate(queries):
        query_text = qr["query"]
        raw = qr["raw_data"]
        cands = _extract_candidates(raw, query_text, qidx)

        base = []
        for c in cands:
            if c.price <= 0: continue
            if c.rating and c.rating < min_rating: continue
            if c.reviews and c.reviews < min_reviews: continue
            if per_cap and c.price > per_cap * cap_flex: continue
            base.append(c)

        if not base:
            base = [c for c in cands if c.price > 0]

        q_tokens = _tokenize(query_text)
        for c in base:
            c.score = _score_candidate(
                c, style_tokens, q_tokens, per_cap,
                notes_tokens, selected_categories_set
            )
        base.sort(key=lambda x: x.score, reverse=True)
        per_query_pools.append(base)

    # initial picks
    picks: List[Optional[Candidate]] = [pool[0] if pool else None for pool in per_query_pools]

    # enforce category diversity
    used_cats = set()
    for i, it in enumerate(picks):
        if not it: continue
        if it.category in used_cats:
            pool = per_query_pools[i]
            repl = next((c for c in pool[1:] if c.category not in used_cats), None)
            if repl: picks[i] = repl
        used_cats.add(picks[i].category if picks[i] else "")

    # budget reconciliation
    def total_cost(items: List[Optional[Candidate]]) -> float:
        return sum((i.price for i in items if i), 0.0)

    if budget and total_cost(picks) > budget:
        changed = True
        while changed and total_cost(picks) > budget:
            changed = False
            ratios: List[Tuple[float, int]] = []
            for i, it in enumerate(picks):
                if not it or it.price <= 0: continue
                ratios.append((it.score / max(1.0, it.price), i))
            if not ratios: break
            _, worst_idx = min(ratios, key=lambda t: t[0])
            pool = per_query_pools[worst_idx]
            if len(pool) > 1:
                curr = picks[worst_idx]
                for alt in pool[1:]:
                    cats_now = {p.category for p in picks if p}
                    cats_now.discard(curr.category)
                    if alt.category in cats_now: continue
                    trial = picks[:]
                    trial[worst_idx] = alt
                    if total_cost(trial) <= budget or (alt.score/alt.price) > (curr.score/curr.price):
                        picks = trial
                        changed = True
                        break

    # dedupe ASINs
    seen_asin = set()
    for i, it in enumerate(picks):
        if not it: continue
        if it.asin and it.asin in seen_asin:
            pool = per_query_pools[i]
            repl = next((c for c in pool if c.asin not in seen_asin and c.category not in {p.category for p in picks if p}), None)
            if repl: picks[i] = repl
        if picks[i] and picks[i].asin: seen_asin.add(picks[i].asin)

    # final results
    return [it.to_result() for it in picks if it]
