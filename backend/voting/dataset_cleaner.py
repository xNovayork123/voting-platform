"""
voting/dataset_cleaner.py
─────────────────────────
Stateless cleaning helpers used by the admin import action.
Each function receives a list-of-dicts (rows) and returns
(cleaned_rows, stats_dict) so nothing is mutated in place.
"""

import re
import json
import csv
import io
from datetime import datetime, timezone


# ─── Low-level helpers ────────────────────────────────────────────────────────

def _normalize_text(value: str) -> str:
    """Strip leading/trailing whitespace and collapse inner whitespace."""
    return re.sub(r"\s+", " ", value.strip()) if value else ""


def _normalize_email(value: str) -> str:
    return value.strip().lower() if value else ""


def _normalize_date(value: str) -> str:
    """Try several date formats; return ISO-8601 string or empty."""
    if not value:
        return ""
    value = value.strip()
    formats = [
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
        "%d-%m-%Y", "%m-%d-%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).isoformat()
        except ValueError:
            continue
    return value  # return as-is if unrecognized


def _normalize_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_json_field(value: str):
    """Try to parse a JSON-encoded field; fall back to a simple list split."""
    if not value:
        return []
    value = value.strip()
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    # Fallback: comma-separated plain text
    return [item.strip() for item in value.split(",") if item.strip()]


# ─── Per-model cleaning functions ─────────────────────────────────────────────

def clean_user_rows(raw_rows: list[dict]) -> tuple[list[dict], dict]:
    """
    Expected CSV columns:
        email, username, password, is_staff, is_superuser, is_active
    """
    cleaned = []
    stats = {
        "rows_total":        len(raw_rows),
        "rows_duplicates":   0,
        "rows_missing":      0,
        "rows_standardized": 0,
        "rows_imported":     0,
    }
    seen_emails: set[str] = set()
    required_fields = {"email"}

    for row in raw_rows:
        original = dict(row)

        # 1. Normalize field names (lower-strip keys)
        row = {k.strip().lower(): v for k, v in row.items()}

        # 2. Check required fields
        email = _normalize_email(row.get("email", ""))
        if not email:
            stats["rows_missing"] += 1
            continue

        # 3. Remove duplicates (within the file)
        if email in seen_emails:
            stats["rows_duplicates"] += 1
            continue
        seen_emails.add(email)

        # 4. Fill missing optional fields with sensible defaults
        username   = _normalize_text(row.get("username", "")) or email.split("@")[0]
        is_staff   = _normalize_bool(row.get("is_staff", "false"))
        is_super   = _normalize_bool(row.get("is_superuser", "false"))
        is_active  = _normalize_bool(row.get("is_active", "true"))
        password   = row.get("password", "").strip() or None  # None → unusable password

        # Track whether we standardized anything
        if username != row.get("username", "").strip():
            stats["rows_standardized"] += 1

        cleaned.append({
            "email":        email,
            "username":     username,
            "password":     password,
            "is_staff":     is_staff,
            "is_superuser": is_super,
            "is_active":    is_active,
        })

    stats["rows_imported"] = len(cleaned)
    return cleaned, stats


def clean_ballot_rows(raw_rows: list[dict]) -> tuple[list[dict], dict]:
    """
    Expected CSV columns:
        title, description, options, category, start_date, end_date, status
    """
    cleaned = []
    stats = {
        "rows_total":        len(raw_rows),
        "rows_duplicates":   0,
        "rows_missing":      0,
        "rows_standardized": 0,
        "rows_imported":     0,
    }
    seen_titles: set[str] = set()

    valid_categories = {
        "general", "music", "gaming", "sports",
        "technology", "food", "travel", "movies", "other",
    }
    valid_statuses = {"open", "closed"}

    now_iso = datetime.now(timezone.utc).isoformat()
    week_iso = datetime(
        datetime.now().year,
        datetime.now().month,
        min(datetime.now().day + 7, 28),
        tzinfo=timezone.utc,
    ).isoformat()

    for row in raw_rows:
        row = {k.strip().lower(): v for k, v in row.items()}

        title = _normalize_text(row.get("title", ""))
        if not title:
            stats["rows_missing"] += 1
            continue

        if title.lower() in seen_titles:
            stats["rows_duplicates"] += 1
            continue
        seen_titles.add(title.lower())

        options_raw = row.get("options", "")
        options = _parse_json_field(options_raw)
        if len(options) < 2:
            stats["rows_missing"] += 1
            continue

        category = row.get("category", "general").strip().lower()
        if category not in valid_categories:
            category = "general"
            stats["rows_standardized"] += 1

        status = row.get("status", "open").strip().lower()
        if status not in valid_statuses:
            status = "open"
            stats["rows_standardized"] += 1

        start_date = _normalize_date(row.get("start_date", "")) or now_iso
        end_date   = _normalize_date(row.get("end_date",   "")) or week_iso

        cleaned.append({
            "title":       title,
            "description": _normalize_text(row.get("description", "")),
            "options":     options,
            "category":    category,
            "start_date":  start_date,
            "end_date":    end_date,
            "status":      status,
        })

    stats["rows_imported"] = len(cleaned)
    return cleaned, stats


# ─── File parser ──────────────────────────────────────────────────────────────

def parse_uploaded_file(file_obj) -> list[dict]:
    """
    Accept CSV or JSON uploaded file objects.
    Returns a list of dicts (one per row/record).
    """
    name = getattr(file_obj, "name", "").lower()
    raw_bytes = file_obj.read()

    if name.endswith(".json"):
        data = json.loads(raw_bytes.decode("utf-8-sig"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Support {users: [...]} or {ballots: [...]} wrappers
            for key in ("users", "ballots", "data", "records", "items"):
                if key in data and isinstance(data[key], list):
                    return data[key]
        raise ValueError("JSON must be an array of objects (or a dict with a known list key).")

    # Default: CSV
    text = raw_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)
