"""
voting/dataset_importer.py
──────────────────────────
Imports cleaned rows into the database for each supported target model.
Returns a dict with counts of created / skipped records.
"""

from django.contrib.auth.models import User
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from .models import Ballot


def import_users(cleaned_rows: list[dict]) -> dict:
    """
    Upsert users from cleaned rows.
    - Creates user if email doesn't exist.
    - Updates is_staff / is_superuser / is_active for existing users.
    - Sets a usable password only when one is provided.
    """
    created = 0
    updated = 0
    errors  = []

    for row in cleaned_rows:
        email    = row["email"]
        username = row["username"]

        try:
            user, new = User.objects.get_or_create(
                username=username,
                defaults={
                    "email":        email,
                    "is_staff":     row["is_staff"],
                    "is_superuser": row["is_superuser"],
                    "is_active":    row["is_active"],
                },
            )

            if new:
                # Set password (or unusable if none supplied)
                if row.get("password"):
                    user.set_password(row["password"])
                else:
                    user.set_unusable_password()
                user.save()
                created += 1
            else:
                # Update permission flags for existing users
                changed = False
                for field in ("is_staff", "is_superuser", "is_active"):
                    if getattr(user, field) != row[field]:
                        setattr(user, field, row[field])
                        changed = True
                if row.get("password"):
                    user.set_password(row["password"])
                    changed = True
                if changed:
                    user.save()
                updated += 1

        except Exception as exc:
            errors.append(f"Row {email}: {exc}")

    return {"created": created, "updated": updated, "errors": errors}


def import_ballots(cleaned_rows: list[dict]) -> dict:
    """
    Upsert ballots from cleaned rows.
    - Creates ballot if title doesn't exist (case-insensitive).
    - Updates fields for existing ballots.
    """
    created = 0
    updated = 0
    errors  = []

    for row in cleaned_rows:
        title = row["title"]
        try:
            # Parse ISO datetime strings
            start = parse_datetime(row["start_date"]) or timezone.now()
            end   = parse_datetime(row["end_date"])   or timezone.now()

            # Make datetimes timezone-aware if they aren't already
            if start.tzinfo is None:
                start = timezone.make_aware(start)
            if end.tzinfo is None:
                end = timezone.make_aware(end)

            ballot, new = Ballot.objects.get_or_create(
                title__iexact=title,
                defaults={
                    "title":       title,
                    "description": row["description"],
                    "options":     row["options"],
                    "category":    row["category"],
                    "start_date":  start,
                    "end_date":    end,
                    "status":      row["status"],
                },
            )

            if not new:
                ballot.description = row["description"]
                ballot.options     = row["options"]
                ballot.category    = row["category"]
                ballot.start_date  = start
                ballot.end_date    = end
                ballot.status      = row["status"]
                ballot.save()
                updated += 1
            else:
                created += 1

        except Exception as exc:
            errors.append(f"Row '{title}': {exc}")

    return {"created": created, "updated": updated, "errors": errors}
