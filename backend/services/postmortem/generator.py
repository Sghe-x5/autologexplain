"""
Markdown postmortem generator.

Берёт на вход dict'ы из API-слоя (не ходит напрямую в ClickHouse), собирает
структурированный markdown-отчёт по готовому шаблону.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Sequence


@dataclass
class PostmortemInput:
    incident: dict  # {incident_id, service, environment, category, severity, title, ...}
    timeline_events: Sequence[dict] = field(default_factory=list)
    evidence_candidates: Sequence[dict] = field(default_factory=list)
    similar_incidents: Sequence[dict] = field(default_factory=list)
    evidence_templates: Sequence[str] = field(default_factory=list)
    author: str = "auto-generator"


def _fmt_dt(v) -> str:
    if not v:
        return "—"
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M UTC")
    s = str(v)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).strftime(
            "%Y-%m-%d %H:%M UTC"
        )
    except Exception:
        return s


def _fmt_rca_breakdown(ctx_json: str | dict) -> str:
    if isinstance(ctx_json, str):
        try:
            ctx = json.loads(ctx_json) if ctx_json else {}
        except Exception:
            return ""
    else:
        ctx = ctx_json or {}
    bd = ctx.get("rca_breakdown") or {}
    if not bd:
        return ""
    lines = []
    weights = {"anomaly": 0.35, "earliness": 0.25, "fanout": 0.2, "criticality": 0.2}
    for k in ("anomaly", "earliness", "fanout", "criticality"):
        v = bd.get(k)
        if v is not None:
            w = weights.get(k, 0.0)
            lines.append(f"  - `{k}` × {w}: **{v:.3f}**")
    return "\n".join(lines)


def _fmt_event(event: dict) -> str:
    etype = event.get("event_type", "event")
    time = _fmt_dt(event.get("event_time"))
    actor = event.get("actor", "system")
    payload = event.get("payload") or {}
    label_map = {
        "opened": "Инцидент открыт",
        "candidate_attached": "Прикреплён кандидат-сигнал",
        "reopened": "Инцидент переоткрыт",
        "rca_recomputed": "RCA пересчитан",
        "status_changed": "Изменение статуса",
    }
    label = label_map.get(etype, etype)
    line = f"- **{time}** · _{label}_ · actor: `{actor}`"
    # Лёгкий анноус ключевых payload-полей
    if etype == "rca_recomputed" and isinstance(payload, dict):
        rcs = payload.get("root_cause_service")
        rcsc = payload.get("root_cause_score")
        if rcs:
            line += f"  \n    root_cause_service=`{rcs}`"
            if rcsc is not None:
                line += f", score={rcsc:.3f}"
    return line


def generate_postmortem(inp: PostmortemInput) -> str:
    inc = inp.incident
    iid = inc.get("incident_id", "?")
    title = inc.get("title", "incident")
    service = inc.get("service", "?")
    env = inc.get("environment", "?")
    category = inc.get("category", "?")
    severity = inc.get("severity", "?")
    status = inc.get("status", "?")
    opened_at = _fmt_dt(inc.get("opened_at"))
    resolved_at = _fmt_dt(inc.get("resolved_at"))
    root_cause_service = inc.get("root_cause_service") or "не определён"
    root_cause_score = inc.get("root_cause_score")
    impact_score = inc.get("impact_score")
    burn_1h = inc.get("burn_rate_1h")
    affected = inc.get("affected_services")
    fingerprint = inc.get("fingerprint", "")

    rca_breakdown = _fmt_rca_breakdown(inc.get("context_json") or inc.get("context") or "")

    md: list[str] = []
    md.append(f"# Postmortem: {title}")
    md.append("")
    md.append(f"**Incident ID:** `{iid}`  ")
    md.append(f"**Fingerprint:** `{fingerprint}`  ")
    md.append(f"**Автор отчёта:** {inp.author} (автоматически сгенерировано)")
    md.append("")
    md.append(f"> _Этот документ сгенерирован автоматически по данным системы. "
              f"Перед публикацией заполните раздел «Action items» и перепроверьте выводы._")
    md.append("")

    # ── Summary
    md.append("## 1. Summary")
    md.append("")
    md.append(
        f"В сервисе `{service}` ({env}, категория `{category}`) зафиксирован "
        f"инцидент со severity **{severity}**."
    )
    md.append(
        f"Система автоматически определила root cause в сервисе **{root_cause_service}**"
        + (f" (RCA score {root_cause_score:.2f})" if isinstance(root_cause_score, (int, float)) else "")
        + "."
    )
    if isinstance(affected, int) and affected > 0:
        md.append(f"Затронуто сервисов: **{affected}**.")
    if isinstance(burn_1h, (int, float)):
        md.append(f"SLO burn rate за 1 час: **{burn_1h:.1f}×**.")
    md.append("")

    # ── Timing
    md.append("## 2. Timing")
    md.append("")
    md.append(f"- Открыт: **{opened_at}**")
    ack = _fmt_dt(inc.get("acknowledged_at"))
    mit = _fmt_dt(inc.get("mitigated_at"))
    md.append(f"- Принят к работе: {ack}")
    md.append(f"- Подавлен: {mit}")
    md.append(f"- Решён: {resolved_at}")
    md.append(f"- Текущий статус: `{status}`")
    md.append("")

    # ── RCA
    md.append("## 3. Root cause (автоматический RCA)")
    md.append("")
    md.append(f"Сервис: **`{root_cause_service}`**")
    if isinstance(root_cause_score, (int, float)):
        md.append(f"Суммарный RCA-score: **{root_cause_score:.3f}**")
    if isinstance(impact_score, (int, float)):
        md.append(f"Impact score: {impact_score:.3f}")
    if rca_breakdown:
        md.append("")
        md.append("Разложение по факторам:")
        md.append(rca_breakdown)
    md.append("")

    # ── Evidence
    md.append("## 4. Evidence")
    md.append("")
    if inp.evidence_templates:
        md.append("**Log-шаблоны (Drain, top-3):**")
        for t in inp.evidence_templates[:3]:
            md.append(f"- `{t}`")
        md.append("")
    if inp.evidence_candidates:
        md.append("**Candidate-сигналы:**")
        for ev in inp.evidence_candidates[:5]:
            payload = ev.get("payload") or {}
            cid = payload.get("candidate_id") or ev.get("event_id", "?")
            score = payload.get("anomaly_score")
            trace_ids = payload.get("trace_ids") or []
            line = f"- candidate_id=`{cid}`"
            if score is not None:
                line += f", anomaly_score={score:.2f}"
            if trace_ids:
                line += f", trace_ids: {', '.join(f'`{t}`' for t in trace_ids[:3])}"
            md.append(line)
        md.append("")
    if not inp.evidence_templates and not inp.evidence_candidates:
        md.append("_Evidence не зафиксировано._")
        md.append("")

    # ── Timeline
    md.append("## 5. Timeline")
    md.append("")
    if inp.timeline_events:
        events_sorted = sorted(inp.timeline_events, key=lambda e: e.get("event_time") or "")
        for ev in events_sorted:
            md.append(_fmt_event(ev))
    else:
        md.append("_События не зафиксированы._")
    md.append("")

    # ── Similar incidents
    md.append("## 6. Похожие инциденты")
    md.append("")
    if inp.similar_incidents:
        md.append("| # | Service | Category | Severity | Similarity | Opened |")
        md.append("|---|---|---|---|---:|---|")
        for i, m in enumerate(inp.similar_incidents[:5], start=1):
            cand = m.get("incident") or m
            md.append(
                f"| {i} | `{cand.get('service','?')}` | "
                f"`{cand.get('category','?')}` | "
                f"`{cand.get('severity','?')}` | "
                f"{m.get('score', 0):.2f} | "
                f"{_fmt_dt(cand.get('opened_at'))} |"
            )
    else:
        md.append("_Похожих инцидентов в истории не найдено._")
    md.append("")

    # ── Action items (template)
    md.append("## 7. Action items")
    md.append("")
    md.append("_Заполните вручную перед публикацией._")
    md.append("")
    md.append("- [ ] Определить корневую причину на уровне кода/инфраструктуры")
    md.append("- [ ] Добавить alerting на early signal (если ещё не было)")
    md.append("- [ ] Runbook: что делать оncall-у при повторении")
    md.append("- [ ] Regression test / мониторинг metric, покрывающий этот сценарий")
    md.append("")

    # ── Lessons learned
    md.append("## 8. Lessons learned")
    md.append("")
    md.append("_Заполните вручную: что сработало хорошо, что можно улучшить в процессе._")
    md.append("")

    return "\n".join(md)
