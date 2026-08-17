"""
canonical.py — map messy raw metric labels onto a controlled vocabulary.

Strategy (layered, most-trusted first):
  1. exact match on a normalized alias      -> method="alias",   high confidence
  2. keyword-rule match (all keywords present) -> method="keyword", medium confidence
  3. no match                                -> method="unmapped", canonical=None (flag for review)

The synonym dictionary is the backbone: deterministic, transparent, easy to audit
and extend. New/unseen labels fall through to "unmapped" rather than being guessed,
which is where a human (or an LLM proposing mappings for human approval) would step in.
"""

import re

# ---------- controlled vocabulary ----------
# canonical_key -> {display, unit, aliases}
# aliases are compared after normalization (lowercase, punctuation -> space, collapsed)

CANONICAL_METRICS = {
    "arr": {
        "display": "ARR",
        "unit": "currency",
        "aliases": [
            "arr", "contracted arr", "annual recurring revenue",
            "recurring revenue annualized","end of period arr", "subscription arr end of period"
        ],
    },
    "revenue": {
        "display": "Revenue",
        "unit": "currency",
        "aliases": [
            "revenue", "quarterly revenue", "quarterly revenue recognized",
            "total recognized revenue", "total revenue","recognized revenue",
        ],
    },
    "gross_margin": {
        "display": "Gross Margin",
        "unit": "pct",
        "aliases": ["gross margin", "gm"],
    },
    "nrr": {
        "display": "Net Revenue Retention",
        "unit": "pct",
        "aliases": ["net revenue retention", "net revenue retention ltm", "nrr","net dollar retention ltm"],
    },
    "grr": {
        "display": "Gross Revenue Retention",
        "unit": "pct",
        "aliases": ["gross revenue retention", "gross revenue retention ltm", "grr"],
    },
    "headcount": {
        "display": "Headcount",
        "unit": "count",
        "aliases": ["headcount", "total headcount", "fte", "employees"],
    },
    "cash_balance": {
        "display": "Cash Balance",
        "unit": "currency",
        "aliases": ["cash balance", "cash", "cash on hand"],
    },
    "net_burn": {
        "display": "Net Burn",
        "unit": "currency",
        "aliases": ["net burn", "monthly net burn", "cash burn"],
    },
    "take_rate": {
        "display": "Take Rate",
        "unit": "pct",
        "aliases": ["take rate", "average take rate"],
    },
    "on_time_delivery_rate": {
        "display": "On-Time Delivery Rate",
        "unit": "pct",
        "aliases": ["on time delivery rate", "otd", "on time delivery"],
    },
    "logo_churn": {
        "display": "Logo Churn",
        "unit": "pct",
        "aliases": ["logo churn", "logo churn ltm", "customer churn", "logo attrition"],
    }
}

# ---------- optional keyword fallback (lower confidence) ----------
# each rule: canonical_key -> set of tokens that must ALL be present in the
# normalized label. Deliberately conservative to avoid false matches.
KEYWORD_RULES = {
    "arr": {"arr"},
    "revenue": {"revenue"},
    "headcount": {"headcount"},
    "gross_margin": {"gross", "margin"},
    "nrr": {"net", "retention"},
    "grr": {"gross", "retention"},
}


# ---------- normalization ----------

def normalize(label):
    """'Net Revenue Retention (LTM)' -> 'net revenue retention ltm'"""
    s = label.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)   # punctuation/symbols -> space
    return re.sub(r"\s+", " ", s).strip()


# build reverse lookup: normalized alias -> canonical_key
_ALIAS_LOOKUP = {}
for key, cfg in CANONICAL_METRICS.items():
    for alias in cfg["aliases"]:
        _ALIAS_LOOKUP[normalize(alias)] = key


# ---------- the resolver ----------

def canonicalize(raw_label):
    """
    Returns dict: {canonical, display, expected_unit, method, confidence}
    canonical is None when unmapped.
    """
    norm = normalize(raw_label)

    # layer 1: exact normalized alias
    if norm in _ALIAS_LOOKUP:
        key = _ALIAS_LOOKUP[norm]
        return _result(key, "alias", "high")

    # layer 2: keyword rules (all tokens present)
    tokens = set(norm.split())
    for key, needed in KEYWORD_RULES.items():
        if needed <= tokens:
            return _result(key, "keyword", "medium")

    # layer 3: unmapped
    return {
        "canonical": None, "display": None, "expected_unit": None,
        "method": "unmapped", "confidence": "none",
    }


def _result(key, method, confidence):
    cfg = CANONICAL_METRICS[key]
    return {
        "canonical": key,
        "display": cfg["display"],
        "expected_unit": cfg["unit"],
        "method": method,
        "confidence": confidence,
    }


# ---------- quick self-test ----------

if __name__ == "__main__":
    samples = [
        "Contracted ARR",
        "Quarterly Revenue (recognized)",
        "Gross Margin",
        "Gross Revenue Retention (LTM)",
        "Net Revenue Retention (LTM)",
        "Total Headcount",
        "Cash Balance",
        "Monthly Net Burn",
        "Average Take Rate",
        "On-Time Delivery Rate",
        "Enterprise Accounts (>$100k ARR)",   # tricky: has 'arr' but isn't ARR
        "SaaS Tool Fee Revenue",              # tricky: revenue component, not total
        "Total Recognized Revenue",
        "Support Tickets / 1,000 Shipments",  # no canonical -> unmapped
    ]
    for s in samples:
        r = canonicalize(s)
        print(f"{s:38s} -> {str(r['canonical']):22s} [{r['method']}/{r['confidence']}]")