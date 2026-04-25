"""
Log template extraction using a simplified Drain algorithm.

Background
──────────
Raw log messages contain both *static* parts (the code-defined text) and
*variable* parts (IP addresses, request IDs, timestamps, counts, …).  Two
log lines emitted by the same ``logger.error(...)`` call look identical
structurally, yet differ in their variable values.

Drain builds a fixed-depth parse tree that routes incoming messages to the
best-matching *log group*.  Each group maintains a *template* — the stable
tokens replaced with a wildcard ``<*>`` wherever values vary.

Parse tree structure (depth = 2):
    Root
    ├── length = 5
    │   ├── prefix = "connection"
    │   │   └── LogGroup id=0  template="connection to <*> refused"  count=42
    │   └── prefix = "query"
    │       └── LogGroup id=1  template="query timeout on <*>"       count=17
    └── length = 8
        └── …

Token similarity between a candidate group and incoming tokens:
    sim(G, T) = |{i : G[i] == T[i]}| / |T|   (only for same-length sequences)

If sim >= SIM_THRESHOLD the message is merged into the group; otherwise a
new group is created.

Reference
─────────
He, P., Zhu, J., Zheng, Z., & Lyu, M. R. (2017).
  Drain: An Online Log Parsing Approach with Fixed Depth Tree.
  2017 IEEE International Conference on Web Services (ICWS), 33–40.
  https://doi.org/10.1109/ICWS.2017.13
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

# ─── Pre-processing patterns (order matters) ────────────────────────────────────

_PREPROCESS: list[tuple[re.Pattern, str]] = [
    # UUID
    (re.compile(r"\b[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\b", re.I), "<*>"),
    # IPv4[:port]
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d{1,5})?\b"),               "<*>"),
    # Hex literal (0x…)
    (re.compile(r"\b0x[0-9a-f]+\b", re.I),                                   "<*>"),
    # Quoted strings
    (re.compile(r"'[^']*'|\"[^\"]*\""),                                       "<*>"),
    # Number with a common unit suffix — time / size / rate / percent.
    # Must come BEFORE the generic integer rule so "100ms" collapses as a
    # single token instead of leaving the "ms" suffix behind (which would
    # otherwise create a spurious second cluster for the same template).
    (re.compile(
        r"(?<!\w)\d+(?:\.\d+)?(?:ms|us|ns|μs|kib|mib|gib|tib|kb|mb|gb|tb|bps|rps|qps|tps|eps|[smhd]|%)(?!\w)",
        re.I,
    ), "<*>"),
    # Generic integer / float.  (?<!\w)/(?!\w) instead of \b so that numbers
    # glued to word characters (e.g. "id=12345x") are not partially matched —
    # consistent with log_fingerprints.py.
    (re.compile(r"(?<!\w)\d+(?:\.\d+)?(?!\w)"),                               "<*>"),
]
_SPACE_RE = re.compile(r"\s+")

_WILDCARD       = "<*>"
_SIM_THRESHOLD  = 0.5    # Fraction of matching positions to merge into a group
_MAX_CHILDREN   = 128    # Max groups per tree node (prevents unbounded growth)


# ─── Core data structures ────────────────────────────────────────────────────────

@dataclass
class LogGroup:
    """A cluster of structurally similar log messages."""

    id:              int
    template_tokens: list[str]   # Template with <*> in variable positions
    log_count:       int = 0

    @property
    def template(self) -> str:
        return " ".join(self.template_tokens)

    def to_dict(self) -> dict:
        return {"id": self.id, "template": self.template, "count": self.log_count}


# ─── Pre-processing helpers ──────────────────────────────────────────────────────

def _preprocess(msg: str) -> str:
    """Replace variable tokens so structurally identical messages tokenize alike."""
    s = msg.lower().strip()
    for pattern, replacement in _PREPROCESS:
        s = pattern.sub(replacement, s)
    return _SPACE_RE.sub(" ", s).strip()


def _tokenize(msg: str) -> list[str]:
    return msg.split() or [_WILDCARD]


# ─── Similarity and template update ─────────────────────────────────────────────

def _token_similarity(template: list[str], tokens: list[str]) -> float:
    """
    Fraction of positions where template and tokens agree.
    Wildcard positions always count as a match.
    Returns 0.0 for sequences of different lengths (they cannot share a group).
    """
    if len(template) != len(tokens):
        return 0.0
    matches = sum(
        1 for a, b in zip(template, tokens)
        if a == b or a == _WILDCARD or b == _WILDCARD
    )
    return matches / len(template)


def _merge_template(template: list[str], tokens: list[str]) -> list[str]:
    """Replace positions that differ between template and incoming tokens with <*>."""
    return [
        a if (a == b or a == _WILDCARD or b == _WILDCARD) else _WILDCARD
        for a, b in zip(template, tokens)
    ]


# ─── Parse tree ──────────────────────────────────────────────────────────────────

class DrainParser:
    """
    Online log parser that maintains a fixed-depth parse tree.

    The tree has two levels:
    • Level 1 — log length (number of tokens after pre-processing)
    • Level 2 — first non-wildcard token (prefix key)

    Each leaf node holds a list of :class:`LogGroup` objects.
    """

    def __init__(
        self,
        sim_threshold: float = _SIM_THRESHOLD,
        max_children: int = _MAX_CHILDREN,
    ) -> None:
        self.sim_threshold = sim_threshold
        self.max_children  = max_children
        # tree[length][prefix] → list[LogGroup]
        self._tree: dict[int, dict[str, list[LogGroup]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._next_id = 0

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _prefix_key(tokens: list[str]) -> str:
        """First non-wildcard token; falls back to a sentinel."""
        for t in tokens:
            if t != _WILDCARD:
                return t
        return "<no-prefix>"

    def _best_match(
        self, candidates: list[LogGroup], tokens: list[str]
    ) -> Optional[tuple[LogGroup, float]]:
        best_group: Optional[LogGroup] = None
        best_sim = -1.0
        for group in candidates:
            sim = _token_similarity(group.template_tokens, tokens)
            if sim > best_sim:
                best_sim, best_group = sim, group
        return (best_group, best_sim) if best_group is not None else None

    # ── Public API ────────────────────────────────────────────────────────────

    def add_log(self, message: str) -> LogGroup:
        """
        Route *message* to the best-matching group, updating its template.
        Creates a new group if no sufficiently similar group exists.
        """
        tokens = _tokenize(_preprocess(message))
        length = len(tokens)
        prefix = self._prefix_key(tokens)
        candidates = self._tree[length][prefix]

        match = self._best_match(candidates, tokens)

        if match is not None:
            group, sim = match
            if sim >= self.sim_threshold:
                group.template_tokens = _merge_template(group.template_tokens, tokens)
                group.log_count += 1
                return group

        # No match — create new group if capacity allows
        if len(candidates) < self.max_children:
            group = LogGroup(id=self._next_id, template_tokens=tokens[:], log_count=1)
            self._next_id += 1
            candidates.append(group)
            return group

        # At capacity: merge into closest existing group
        if match is not None:
            group, _ = match
            group.template_tokens = _merge_template(group.template_tokens, tokens)
            group.log_count += 1
            return group

        return candidates[0]  # unreachable in practice

    def get_templates(self) -> list[LogGroup]:
        """Return all known groups sorted by frequency descending."""
        groups: list[LogGroup] = []
        for length_dict in self._tree.values():
            for candidate_list in length_dict.values():
                groups.extend(candidate_list)
        return sorted(groups, key=lambda g: -g.log_count)


# ─── Public entry point ──────────────────────────────────────────────────────────

def extract_templates(
    enriched_logs: list[dict],
    sim_threshold: float = _SIM_THRESHOLD,
    top_n: int = 20,
) -> dict:
    """
    Extract log templates from a batch of enriched log records.

    Groups structurally similar messages into templates, replacing variable
    parts with ``<*>``.  Returns cluster assignments for every input message
    and a ranked list of the most common templates.

    Parameters
    ──────────
    enriched_logs:
        Output of :func:`~backend.services.log_tags.enrich_log_record`.
    sim_threshold:
        Minimum token-similarity (0–1) to merge a message into an existing
        group.  Lower values produce fewer, coarser clusters.
    top_n:
        Maximum number of templates to return in the summary.

    Returns
    ───────
    ::

        {
            "templates":       [{"id": int, "template": str, "count": int}, …],
            "clustered_logs":  [{"message": str, "template": str, "cluster_id": int}, …],
            "total_logs":      int,
            "unique_templates": int,
        }
    """
    parser = DrainParser(sim_threshold=sim_threshold)

    clustered: list[dict] = []
    for log in enriched_logs:
        msg   = str(log.get("message", ""))
        group = parser.add_log(msg)
        clustered.append({
            "message":    msg,
            "template":   group.template,
            "cluster_id": group.id,
        })

    templates = parser.get_templates()

    return {
        "templates":        [g.to_dict() for g in templates[:top_n]],
        "clustered_logs":   clustered,
        "total_logs":       len(enriched_logs),
        "unique_templates": len(templates),
    }
