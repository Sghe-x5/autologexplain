"""
Unit tests for backend.services.dependency_graph

Tests cover:
- ServiceGraph: add_edge, get_callers, get_callees, all_nodes, filtered, to_dict
- build_graph_from_traces(): directed edge inference from trace data
- find_cascade_root(): root cause detection heuristic
- reconstruct_cascade_path(): BFS cascade path reconstruction
"""

from backend.services.dependency_graph import (
    ServiceGraph,
    build_graph_from_traces,
    find_cascade_root,
    reconstruct_cascade_path,
)


# ─── ServiceGraph ────────────────────────────────────────────────────────────────

def test_add_edge_increments_weight():
    g = ServiceGraph()
    g.add_edge("a", "b")
    g.add_edge("a", "b")
    assert g.edges["a"]["b"] == 2


def test_add_edge_self_loop_ignored():
    g = ServiceGraph()
    g.add_edge("a", "a")
    assert "a" not in g.edges.get("a", {})


def test_get_callees():
    g = ServiceGraph()
    g.add_edge("api", "auth")
    g.add_edge("api", "db")
    assert set(g.get_callees("api")) == {"auth", "db"}
    assert g.get_callees("unknown") == []


def test_get_callers():
    g = ServiceGraph()
    g.add_edge("api",  "db")
    g.add_edge("auth", "db")
    callers = g.get_callers("db")
    assert "api"  in callers
    assert "auth" in callers


def test_all_nodes():
    g = ServiceGraph()
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    assert g.all_nodes() == {"a", "b", "c"}


def test_filtered_removes_low_weight():
    g = ServiceGraph()
    g.add_edge("a", "b", weight=5)
    g.add_edge("a", "c", weight=1)
    filtered = g.filtered(min_weight=3)
    assert "b" in filtered.edges.get("a", {})
    assert "c" not in filtered.edges.get("a", {})


def test_filtered_keeps_high_weight():
    g = ServiceGraph()
    g.add_edge("x", "y", weight=10)
    filtered = g.filtered(min_weight=3)
    assert filtered.edges["x"]["y"] == 10


def test_to_dict_structure():
    g = ServiceGraph()
    g.add_edge("api", "db")
    d = g.to_dict()
    assert "nodes" in d
    assert "edges" in d
    assert {"from": "api", "to": "db", "weight": 1} in d["edges"]


# ─── build_graph_from_traces ─────────────────────────────────────────────────────

def _trace(trace_id, *service_times):
    """Helper: list of trace records for (service, timestamp) pairs."""
    return [
        {"trace_id": trace_id, "service": svc, "first_ts": ts}
        for svc, ts in service_times
    ]


def test_build_graph_basic_edge():
    data = _trace("t1",
        ("api",  "2024-01-01T10:00:00"),
        ("auth", "2024-01-01T10:00:01"),
    )
    # Only 1 occurrence → below default MIN_EDGE_WEIGHT=3, so filtered out
    # Test with manual graph build
    from backend.services.dependency_graph import _MIN_EDGE_WEIGHT
    # Build 3 traces to exceed threshold
    all_data = data * _MIN_EDGE_WEIGHT
    # But they all have the same trace_id so they'll be grouped into one
    # Use distinct trace ids
    traces = []
    for i in range(_MIN_EDGE_WEIGHT):
        traces += _trace(f"t{i}",
            ("api",  f"2024-01-01T10:0{i}:00"),
            ("auth", f"2024-01-01T10:0{i}:01"),
        )
    graph = build_graph_from_traces(traces)
    callees = graph.get_callees("api")
    assert "auth" in callees


def test_build_graph_respects_temporal_order():
    # auth logs before api → auth → api edge
    traces = []
    for i in range(3):
        traces += _trace(f"t{i}",
            ("auth", f"2024-01-01T10:0{i}:00"),
            ("api",  f"2024-01-01T10:0{i}:01"),
        )
    graph = build_graph_from_traces(traces)
    assert "api" in graph.get_callees("auth")
    assert "auth" not in graph.get_callees("api")


def test_build_graph_empty_trace_data():
    graph = build_graph_from_traces([])
    assert graph.all_nodes() == set()


def test_build_graph_skips_empty_trace_id():
    data = [{"trace_id": "", "service": "api", "first_ts": "2024-01-01T10:00:00"}]
    graph = build_graph_from_traces(data)
    assert graph.all_nodes() == set()


def test_build_graph_single_service_trace_no_edge():
    data = [{"trace_id": "t1", "service": "api", "first_ts": "2024-01-01T10:00:00"}]
    graph = build_graph_from_traces(data)
    # No pairs → no edges
    assert graph.all_nodes() == set() or not any(graph.edges.values())


# ─── find_cascade_root ────────────────────────────────────────────────────────────

def _simple_graph(*edges) -> ServiceGraph:
    g = ServiceGraph()
    for caller, callee in edges:
        g.add_edge(caller, callee, weight=5)
    return g


def test_find_root_no_upstream_anomalous_caller():
    # auth → api → frontend  (auth fires first)
    graph = _simple_graph(("auth", "api"), ("api", "frontend"))
    times = {"auth": "10:00", "api": "10:01", "frontend": "10:02"}
    root = find_cascade_root(["auth", "api", "frontend"], graph, times)
    assert root == "auth"


def test_find_root_no_anomalous_services():
    graph = _simple_graph(("a", "b"))
    assert find_cascade_root([], graph, {}) is None


def test_find_root_prefers_earliest_among_candidates():
    # Both api and worker have no anomalous callers; api fires earlier
    graph = ServiceGraph()  # no edges between them
    times = {"api": "10:00", "worker": "10:05"}
    root = find_cascade_root(["api", "worker"], graph, times)
    assert root == "api"


def test_find_root_prefers_service_with_downstream():
    # db → api (in graph); both anomalous; db fires first and has downstream
    graph = _simple_graph(("db", "api"))
    times = {"db": "10:00", "api": "10:01"}
    root = find_cascade_root(["db", "api"], graph, times)
    assert root == "db"


# ─── reconstruct_cascade_path ─────────────────────────────────────────────────────

def test_cascade_path_single_node():
    graph = ServiceGraph()
    path = reconstruct_cascade_path("api", {"api"}, graph)
    assert path == ["api"]


def test_cascade_path_follows_anomalous_services():
    # auth → api → frontend (all anomalous, edges in graph)
    graph = _simple_graph(("auth", "api"), ("api", "frontend"))
    anomalous = {"auth", "api", "frontend"}
    path = reconstruct_cascade_path("auth", anomalous, graph)
    assert path[0] == "auth"
    assert "api" in path
    assert "frontend" in path


def test_cascade_path_skips_non_anomalous():
    # auth → api → db, but db is NOT anomalous
    graph = _simple_graph(("auth", "api"), ("api", "db"))
    anomalous = {"auth", "api"}
    path = reconstruct_cascade_path("auth", anomalous, graph)
    assert "db" not in path


def test_cascade_path_respects_max_depth():
    # Long chain: 0→1→2→...→9
    graph = ServiceGraph()
    for i in range(9):
        graph.add_edge(str(i), str(i + 1), weight=5)
    anomalous = {str(i) for i in range(10)}
    path = reconstruct_cascade_path("0", anomalous, graph, max_depth=4)
    assert len(path) <= 4
