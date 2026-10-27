"""
voting/dataset_exporter.py
──────────────────────────
Export the current database records to CSV or JSON.
Returns an HttpResponse ready to send to the browser.
"""

import csv
import json
import io
from datetime import datetime, timezone as dt_tz

from django.http import HttpResponse
from django.contrib.auth.models import User

from .models import Ballot


def _utc_now_str() -> str:
    return datetime.now(dt_tz.utc).strftime("%Y%m%d_%H%M%S")


# ─── Users ────────────────────────────────────────────────────────────────────

USER_FIELDS = [
    "id", "email", "username",
    "is_staff", "is_superuser", "is_active",
    "date_joined", "last_login",
]


def _user_rows(queryset=None):
    qs = queryset or User.objects.all().order_by("id")
    rows = []
    for u in qs:
        rows.append({
            "id":           u.id,
            "email":        u.email,
            "username":     u.username,
            "is_staff":     u.is_staff,
            "is_superuser": u.is_superuser,
            "is_active":    u.is_active,
            "date_joined":  u.date_joined.isoformat() if u.date_joined else "",
            "last_login":   u.last_login.isoformat()  if u.last_login  else "",
        })
    return rows


def export_users_csv(queryset=None) -> HttpResponse:
    rows = _user_rows(queryset)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=USER_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    response = HttpResponse(buf.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="users_export_{_utc_now_str()}.csv"'
    )
    return response


def export_users_json(queryset=None) -> HttpResponse:
    rows = _user_rows(queryset)
    response = HttpResponse(
        json.dumps(rows, indent=2, default=str),
        content_type="application/json",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="users_export_{_utc_now_str()}.json"'
    )
    return response


# ─── Ballots ──────────────────────────────────────────────────────────────────

BALLOT_FIELDS = [
    "id", "title", "description", "options",
    "category", "start_date", "end_date", "status", "created_at",
]


def _ballot_rows(queryset=None):
    qs = queryset or Ballot.objects.all().order_by("-created_at")
    rows = []
    for b in qs:
        rows.append({
            "id":          b.id,
            "title":       b.title,
            "description": b.description,
            "options":     json.dumps(b.options),   # serialize list → JSON string for CSV
            "category":    b.category,
            "start_date":  b.start_date.isoformat() if b.start_date else "",
            "end_date":    b.end_date.isoformat()   if b.end_date   else "",
            "status":      b.status,
            "created_at":  b.created_at.isoformat() if b.created_at else "",
        })
    return rows


def export_ballots_csv(queryset=None) -> HttpResponse:
    rows = _ballot_rows(queryset)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=BALLOT_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    response = HttpResponse(buf.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="ballots_export_{_utc_now_str()}.csv"'
    )
    return response


def export_ballots_json(queryset=None) -> HttpResponse:
    qs = queryset or Ballot.objects.all().order_by("-created_at")
    rows = []
    for b in qs:
        rows.append({
            "id":          b.id,
            "title":       b.title,
            "description": b.description,
            "options":     b.options,   # keep as native list in JSON
            "category":    b.category,
            "start_date":  b.start_date.isoformat() if b.start_date else "",
            "end_date":    b.end_date.isoformat()   if b.end_date   else "",
            "status":      b.status,
            "created_at":  b.created_at.isoformat() if b.created_at else "",
        })
    response = HttpResponse(
        json.dumps(rows, indent=2, default=str),
        content_type="application/json",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="ballots_export_{_utc_now_str()}.json"'
    )
    return response
