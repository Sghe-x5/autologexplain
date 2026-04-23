"""
Automatic service dependency graph inferred from distributed trace data.

Motivation
──────────
In a microservices architecture, a single user request typically spans
multiple services.  Distributed tracing tools (Jaeger, Zipkin, …) assign
the same ``trace_id`` to all log records produced while processing that
request.  By observing *which services appear together in the same trace*
and in *what time order*, we can infer a directed call graph without any
code instrumentation.

Algorithm
─────────
1. Query ClickHouse for ``(trace_id, service, min(timestamp))`` tuples.
2. For every trace, sort services by their first-seen timestamp.
3. For each consecutive pair (A, B) in the sorted list, record the directed
   edge A → B (A called B, because A logged first in this trace).
4. Aggregate edge weights; discard edges whose weight falls below
   ``MIN_EDGE_WEIGHT`` (reduces noise from accidental co-occurrence).

Cascade root detection
──────────────────────
Given a set of *anomalous* services (from :mod:`anomaly_detector`):
1. Find the subset with no anomalous *callers* in the dependency graph —
   these are candidates for the cascade origin.
2. Among candidates, pick the one whose anomaly started earliest.
3. Verify it has anomalous *downstream* dependents (cascade confirmation).

If no dependency data is available the heuristic degrades gracefully to
"pick the service with the earliest anomaly onset".

Reference
─────────
Chen, P., Qi, Y., & Hou, D. (2014).
  Causeinfer: Automatic and distributed performance diagnosis with
  hierarchical causality graph in large distributed systems.
  IEEE INFOCOM 2014, 1887–1895.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional

_MIN_EDGE_WEIGHT = 3   # Edges seen fewer times than this are discarded as noise


# ─── Graph model ─────────────────────────────────────────────────────────────────

@dataclass
class ServiceGraph:
    """
    Weighted directed graph of service dependencies.

    ``edges[A][B] = N`` means service A called service B in N distinct traces.
    """

    edges: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )

    # ── Mutation ─────────────────────────────────────────────────────────────

    def add_edge(self, caller: str, callee: str, weight: int = 1) -> None:
        """
        Увеличить вес ребра ``caller → callee`` на ``weight``.

        Self-loops (caller == callee) игнорируются: в graph они не
        несут смысла для cascade-анализа.
        """
        if caller != callee:
            self.edges[caller][callee] += weight

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_callers(self, service: str) -> list[str]:
        """All services known to call *service* (in-neighbours)."""
        return [s for s, callees in self.edges.items() if service in callees]

    def get_callees(self, service: str) -> list[str]:
        """All services that *service* is known to call (out-neighbours)."""
        return list(self.edges.get(service, {}).keys())

    def all_nodes(self) -> set[str]:
        """Все узлы графа (источники + таргеты рёбер)."""
        nodes = set(self.edges.keys())
        for callees in self.edges.values():
            nodes.update(callees.keys())
        return nodes

    # ── Derived graphs ────────────────────────────────────────────────────────

    def filtered(self, min_weight: int = _MIN_EDGE_WEIGHT) -> "ServiceGraph":
        """Return a new graph containing only edges with weight ≥ *min_weight*."""
        g = ServiceGraph()
        for caller, callees in self.edges.items():
            for callee, w in callees.items():
                if w >= min_weight:
                    g.edges[caller][callee] = w
        return g

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "nodes": sorted(self.all_nodes()),
            "edges": [
                {"from": caller, "to": callee, "weight": w}
                for caller, callees in self.edges.items()
                for callee, w in callees.items()
            ],
        }


# ─── Graph construction ──────────────────────────────────────────────────────────

def build_graph_from_traces(trace_data: list[dict]) -> ServiceGraph:
    """
    Construct a :class:`ServiceGraph` from raw trace records.

    Parameters
    ──────────
    trace_data:
        List of dicts with keys ``trace_id``, ``service``, ``first_ts``
        (the minimum timestamp seen for that service in that trace).
        Typically the result of the ClickHouse aggregation query::

            SELECT trace_id, service, min(timestamp) AS first_ts
            FROM logs
            WHERE trace_id != ''
              AND timestamp >= now() - INTERVAL {hours} HOUR
            GROUP BY trace_id, service

    Returns
    ───────
    A :class:`ServiceGraph` with edges filtered to ``MIN_EDGE_WEIGHT``.
    """
    by_trace: dict[str, list[dict]] = defaultdict(list)
    for row in trace_data:
        tid = row.get("trace_id", "")
        if tid:
            by_trace[tid].append(row)

    raw = ServiceGraph()
    for events in by_trace.values():
        ordered = sorted(events, key=lambda r: str(r.get("first_ts", "")))
        services = [str(e["service"]) for e in ordered if e.get("service")]
        for i in range(len(services) - 1):
            raw.add_edge(services[i], services[i + 1])

    return raw.filtered()


# ─── Cascade analysis ────────────────────────────────────────────────────────────

def find_cascade_root(
    anomalous_services: list[str],
    graph: ServiceGraph,
    first_anomaly_times: dict[str, str],   # service → ISO timestamp of first anomaly
) -> Optional[str]:
    """
    Identify the most probable root-cause service in a cascade.

    Strategy
    ────────
    1. Find anomalous services that have *no anomalous callers* in the graph
       (i.e., no upstream service with anomalies called them).  These are
       potential cascade origins.
    2. Among the candidates, pick the one whose anomaly started earliest.
    3. If a candidate has anomalous downstream dependents, it is confirmed as
       a cascade root; otherwise fall back to the earliest-onset service.

    Returns ``None`` if *anomalous_services* is empty.
    """
    if not anomalous_services:
        return None

    anomalous_set = set(anomalous_services)

    def _onset(svc: str) -> str:
        return first_anomaly_times.get(svc, "9999-99-99")

    # Step 1: services with no *earlier-started* anomalous upstream callers.
    # A service whose only anomalous callers started AFTER it cannot have been
    # triggered by them — so it is still a valid cascade origin. This handles
    # cyclic dependency graphs (A↔B↔C) where naive "no anomalous callers"
    # filters out the real root.
    candidates = [
        svc for svc in anomalous_services
        if not any(
            c in anomalous_set and _onset(c) < _onset(svc)
            for c in graph.get_callers(svc)
        )
    ]
    if not candidates:
        candidates = anomalous_services[:]  # fully-connected cycle fallback

    # Step 2: prefer candidates with anomalous downstream services (cascade proof)
    confirmed = [
        c for c in candidates
        if any(callee in anomalous_set for callee in graph.get_callees(c))
    ]
    pool = confirmed if confirmed else candidates
    return min(pool, key=_onset)


def reconstruct_cascade_path(
    root: str,
    anomalous_services: set[str],
    graph: ServiceGraph,
    max_depth: int = 8,
) -> list[str]:
    """
    BFS from *root* through anomalous services in the dependency graph.

    Returns the longest simple path found (root → … → leaf).
    """
    visited: set[str] = {root}
    queue: deque[list[str]] = deque([[root]])
    longest: list[str] = [root]

    while queue:
        path = queue.popleft()
        if len(path) >= max_depth:
            continue
        current = path[-1]
        for callee in graph.get_callees(current):
            if callee in anomalous_services and callee not in visited:
                visited.add(callee)
                new_path = path + [callee]
                if len(new_path) > len(longest):
                    longest = new_path
                queue.append(new_path)

    return longest
