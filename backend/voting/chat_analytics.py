"""
voting/chat_analytics.py
────────────────────────
Stateless frequency / activity analytics for parsed chat messages (SCRUM-26).

    analyze_activity(messages) -> dict

`messages` is the list produced by voting/chat_parser.parse_chat. The result is
a plain dict ready to be serialized to JSON by the API view. No DB access.

Reported metrics:
  * total messages, participants, number of distinct days, date range
  * average messages per day
  * activity by hour (0-23) and the peak hour
  * per participant: message count, average per day, and active hours
"""

from collections import defaultdict


# ─── Helper ─────────────────────────────────────────────────────────────────────
def _round(value, ndigits=2):
    return round(value, ndigits)


# ─── Función principal: analyze_activity() ─────────────────────────────────────
def analyze_activity(messages: list) -> dict:
    """Compute frequency and active-hour metrics for a list of messages."""
    # Caso límite: sin mensajes, se devuelve la misma forma pero "vacía" en vez
    # de dejar que max()/división por cero explote más abajo.
    if not messages:
        return {
            "summary": {
                "total_messages": 0,
                "participants": [],
                "days": 0,
                "avg_messages_per_day": 0,
                "date_range": {"start": None, "end": None},
            },
            "activity_by_hour": [{"hour": h, "count": 0} for h in range(24)],
            "peak_hour": None,
            "per_participant": [],
        }

    # ── Acumuladores ──
    hour_counts = [0] * 24               # mensajes por hora del día (0-23), sumando todos los días
    per_author_count = defaultdict(int)  # total de mensajes por participante
    per_author_hours = defaultdict(set)  # en qué horas estuvo activo cada participante
    distinct_days = set()                # fechas distintas (sin hora), para los promedios
    datetimes = []                       # todos los datetime, para calcular el date_range

    # ── Una sola pasada por todos los mensajes, llenando los acumuladores ──
    for m in messages:
        dt = m["datetime"]
        datetimes.append(dt)
        hour_counts[dt.hour] += 1
        distinct_days.add(dt.date())
        author = m["author"]
        per_author_count[author] += 1
        per_author_hours[author].add(dt.hour)

    # ── Métricas globales ──
    total = len(messages)
    days = len(distinct_days)
    avg_per_day = _round(total / days) if days else 0

    peak_count = max(hour_counts)
    peak_hour = hour_counts.index(peak_count) if peak_count else None  # None si todo quedó en 0

    # ── Métricas por participante (orden alfabético) ──
    per_participant = []
    for author in sorted(per_author_count):
        count = per_author_count[author]
        per_participant.append({
            "name": author,
            "messages": count,
            "avg_per_day": _round(count / days) if days else 0,
            "active_hours": sorted(per_author_hours[author]),
        })

    # ── Armado de la respuesta final (mismo "shape" que el caso vacío de arriba) ──
    return {
        "summary": {
            "total_messages": total,
            "participants": sorted(per_author_count),
            "days": days,
            "avg_messages_per_day": avg_per_day,
            "date_range": {
                "start": min(datetimes).isoformat(),
                "end": max(datetimes).isoformat(),
            },
        },
        "activity_by_hour": [{"hour": h, "count": hour_counts[h]} for h in range(24)],
        "peak_hour": peak_hour,
        "per_participant": per_participant,
    }
