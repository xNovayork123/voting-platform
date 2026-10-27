"""
voting/admin.py
───────────────
Django Admin registrations, including:
 • CustomUserAdmin  – create/edit users + set passwords + bulk actions
 • DatasetImportAdmin  – import CSV/JSON → Users or Ballots with full
     cleaning pipeline (dedup, missing-value handling, format standardisation)
     plus export actions (CSV & JSON) on both Users and Ballots
"""

import datetime
import traceback

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .dataset_cleaner  import parse_uploaded_file, clean_user_rows, clean_ballot_rows
from .dataset_exporter import (
    export_users_csv, export_users_json,
    export_ballots_csv, export_ballots_json,
)
from .dataset_importer import import_users, import_ballots
from .models import (
    Ballot, BallotSuggestion, DatasetImport,
    Document, UserProfile, Vote,
    Announcement, AnnouncementRecipient, FAQ,
    Transaction, Budget,
)


# ══════════════════════════════════════════════════════════════════════════════
#  Custom User Admin
# ══════════════════════════════════════════════════════════════════════════════

class SetPasswordForm(forms.ModelForm):
    new_password = forms.CharField(
        label="Set new password (emergency reset)",
        widget=forms.PasswordInput(render_value=False),
        required=False,
        help_text="Type a new password and save to override the current one. "
                  "Leave blank to keep unchanged.",
    )

    class Meta:
        model  = User
        fields = "__all__"

    def save(self, commit=True):
        user = super().save(commit=False)
        pw = self.cleaned_data.get("new_password")
        if pw:
            user.set_password(pw)
        if commit:
            user.save()
        return user


class UserProfileInline(admin.StackedInline):
    model      = UserProfile
    can_delete = False
    verbose_name = "Profile"
    fields = ("display_name", "status", "profile_picture")
    extra  = 0


class CustomUserAdmin(BaseUserAdmin):
    form    = SetPasswordForm
    inlines = [UserProfileInline]

    list_display       = ("id", "email", "username", "is_staff", "is_superuser", "is_active", "date_joined")
    list_display_links = ("id", "email", "username")
    ordering           = ("id",)
    search_fields      = ("email", "username")
    list_filter        = ("is_staff", "is_superuser", "is_active")

    fieldsets = (
        ("Account", {"fields": ("username", "email", "new_password")}),
        ("Permissions", {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            "description": "Check 'Staff status' AND 'Superuser status' to make this user a full admin.",
        }),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    readonly_fields = ("last_login", "date_joined")

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields":  ("username", "email", "password1", "password2", "is_staff", "is_superuser"),
        }),
    )

    actions = ["make_admin", "remove_admin", "deactivate_users", "activate_users",
               "export_selected_users_csv", "export_selected_users_json"]

    # ── Bulk permission actions ──────────────────────────────────────────────

    @admin.action(description="Make selected users admin (staff + superuser)")
    def make_admin(self, request, queryset):
        updated = queryset.update(is_staff=True, is_superuser=True)
        self.message_user(request, f"{updated} user(s) promoted to admin.")

    @admin.action(description="Remove admin from selected users")
    def remove_admin(self, request, queryset):
        updated = queryset.update(is_staff=False, is_superuser=False)
        self.message_user(request, f"Admin removed from {updated} user(s).")

    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} user(s) deactivated.")

    @admin.action(description="Activate selected users")
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} user(s) activated.")

    # ── Export actions ───────────────────────────────────────────────────────

    @admin.action(description="⬇ Export selected users as CSV")
    def export_selected_users_csv(self, request, queryset):
        return export_users_csv(queryset)

    @admin.action(description="⬇ Export selected users as JSON")
    def export_selected_users_json(self, request, queryset):
        return export_users_json(queryset)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# ══════════════════════════════════════════════════════════════════════════════
#  UserProfile Admin
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display   = ("user_id", "user_email", "display_name", "status")
    search_fields  = ("user__email", "display_name")
    list_filter    = ("status",)

    def user_id(self, obj):    return obj.user.id
    user_id.short_description = "User ID"

    def user_email(self, obj): return obj.user.email
    user_email.short_description = "Email"


# ══════════════════════════════════════════════════════════════════════════════
#  Ballot Admin
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(Ballot)
class BallotAdmin(admin.ModelAdmin):
    list_display   = ("title", "status", "category", "start_date", "end_date", "created_at")
    list_filter    = ("status", "category")
    search_fields  = ("title", "description")
    ordering       = ("-created_at",)
    readonly_fields = ("created_at",)
    actions        = ["export_selected_ballots_csv", "export_selected_ballots_json"]

    fieldsets = (
        ("General", {"fields": ("title", "description", "status", "category")}),
        ("Options", {
            "fields":      ("options",),
            "description": 'Enter options as a JSON list. Example: ["Option A", "Option B"]',
        }),
        ("Dates", {"fields": ("start_date", "end_date", "created_at")}),
    )

    @admin.action(description="⬇ Export selected ballots as CSV")
    def export_selected_ballots_csv(self, request, queryset):
        return export_ballots_csv(queryset)

    @admin.action(description="⬇ Export selected ballots as JSON")
    def export_selected_ballots_json(self, request, queryset):
        return export_ballots_json(queryset)


# ══════════════════════════════════════════════════════════════════════════════
#  Vote Admin
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display   = ("ballot", "option", "user", "timestamp")
    list_filter    = ("ballot", "option")
    ordering       = ("-timestamp",)
    readonly_fields = ("ballot", "option", "user", "timestamp")


# ══════════════════════════════════════════════════════════════════════════════
#  BallotSuggestion Admin
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(BallotSuggestion)
class BallotSuggestionAdmin(admin.ModelAdmin):
    list_display   = ("title", "suggested_by", "status", "created_at")
    list_filter    = ("status",)
    search_fields  = ("title", "description", "suggested_by")
    ordering       = ("-created_at",)
    readonly_fields = ("created_at",)
    actions        = ("approve_suggestions", "reject_suggestions")

    fieldsets = (
        ("Suggestion", {"fields": ("title", "description", "options", "suggested_by")}),
        ("Review",     {"fields": ("status", "admin_note", "created_at")}),
    )

    @admin.action(description="Approve selected suggestions (creates ballots)")
    def approve_suggestions(self, request, queryset):
        created = 0
        for suggestion in queryset:
            if suggestion.status == "approved":
                continue
            suggestion.status = "approved"
            suggestion.save()
            Ballot.objects.create(
                title=suggestion.title,
                description=suggestion.description,
                options=suggestion.options,
                start_date=timezone.now(),
                end_date=timezone.now() + datetime.timedelta(days=7),
                status="open",
            )
            created += 1
        self.message_user(request, f"{created} suggestion(s) approved and turned into ballots.")

    @admin.action(description="Reject selected suggestions")
    def reject_suggestions(self, request, queryset):
        updated = queryset.exclude(status="approved").update(status="rejected")
        self.message_user(request, f"{updated} suggestion(s) rejected.")


# ══════════════════════════════════════════════════════════════════════════════
#  Document Admin
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display   = ("name", "uploaded_by", "category", "size_in_kb", "uploaded_at")
    list_filter    = ("category", "uploaded_at", "uploaded_by")
    search_fields  = ("name", "tags", "uploaded_by__email", "uploaded_by__username")

    def size_in_kb(self, obj):
        return f"{obj.size / 1024:.1f} KB"
    size_in_kb.short_description = "Size"


# ══════════════════════════════════════════════════════════════════════════════
#  Dataset Import Admin
# ══════════════════════════════════════════════════════════════════════════════

class DatasetImportForm(forms.ModelForm):
    """Upload form shown in the Django admin add page."""

    class Meta:
        model  = DatasetImport
        fields = ("file", "target_model", "notes")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["file"].help_text = (
            "Upload a <strong>CSV</strong> or <strong>JSON</strong> file.<br>"
            "<ul>"
            "<li><b>Users CSV columns:</b> email, username, password, is_staff, "
            "is_superuser, is_active</li>"
            "<li><b>Ballots CSV columns:</b> title, description, options (JSON list), "
            "category, start_date, end_date, status</li>"
            "</ul>"
            "The importer will automatically clean, deduplicate, fill missing values, "
            "and standardise formats before saving."
        )


class StatusFilter(SimpleListFilter):
    title        = "Import status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return DatasetImport.STATUS_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


@admin.register(DatasetImport)
class DatasetImportAdmin(admin.ModelAdmin):
    form = DatasetImportForm

    list_display = (
        "id", "target_model_badge", "file_name", "status_badge",
        "rows_total", "rows_imported", "rows_duplicates",
        "rows_missing", "rows_standardized",
        "imported_by", "created_at", "export_links",
    )
    list_filter    = (StatusFilter, "target_model", "created_at")
    search_fields  = ("file", "notes")
    readonly_fields = (
        "status", "rows_total", "rows_imported",
        "rows_duplicates", "rows_missing", "rows_standardized",
        "error_log", "imported_by", "created_at", "finished_at",
        "cleaning_report_display",
    )
    ordering = ("-created_at",)

    # Only show upload fields when creating; show stats when viewing
    def get_fieldsets(self, request, obj=None):
        if obj is None:
            # Add page
            return (
                ("Upload Dataset", {
                    "fields": ("file", "target_model", "notes"),
                    "description": (
                        "Upload a CSV or JSON file and choose the target table. "
                        "The system will automatically clean the data before importing."
                    ),
                }),
            )
        # Change page (read-only result view)
        return (
            ("Import Details", {
                "fields": ("file", "target_model", "notes", "status", "imported_by",
                           "created_at", "finished_at"),
            }),
            ("Cleaning Report", {
                "fields": ("cleaning_report_display",),
            }),
            ("Error Log", {
                "fields":   ("error_log",),
                "classes":  ("collapse",),
            }),
        )

    def get_actions(self, request):
        actions = super().get_actions(request)
        return actions

    # ── Computed display columns ─────────────────────────────────────────────

    def file_name(self, obj):
        return obj.file.name.split("/")[-1] if obj.file else "—"
    file_name.short_description = "File"

    def status_badge(self, obj):
        colours = {
            "pending":    "#6c757d",
            "processing": "#fd7e14",
            "done":       "#28a745",
            "failed":     "#dc3545",
        }
        colour = colours.get(obj.status, "#333")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:600">{}</span>',
            colour, obj.get_status_display(),
        )
    status_badge.short_description = "Status"

    def target_model_badge(self, obj):
        colours = {"users": "#0d6efd", "ballots": "#6610f2"}
        colour  = colours.get(obj.target_model, "#333")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px">{}</span>',
            colour, obj.get_target_model_display(),
        )
    target_model_badge.short_description = "Target"

    def cleaning_report_display(self, obj):
        return format_html(
            "<table style='border-collapse:collapse;width:100%'>"
            "<tr style='background:#f8f9fa'>"
            "  <th style='padding:8px;border:1px solid #dee2e6'>Metric</th>"
            "  <th style='padding:8px;border:1px solid #dee2e6'>Count</th>"
            "</tr>"
            "<tr><td style='padding:8px;border:1px solid #dee2e6'>Total rows in file</td>"
            "    <td style='padding:8px;border:1px solid #dee2e6'><b>{}</b></td></tr>"
            "<tr><td style='padding:8px;border:1px solid #dee2e6'>✅ Successfully imported</td>"
            "    <td style='padding:8px;border:1px solid #dee2e6'><b>{}</b></td></tr>"
            "<tr><td style='padding:8px;border:1px solid #dee2e6'>🔁 Duplicates removed</td>"
            "    <td style='padding:8px;border:1px solid #dee2e6'><b>{}</b></td></tr>"
            "<tr><td style='padding:8px;border:1px solid #dee2e6'>⚠️ Missing required fields</td>"
            "    <td style='padding:8px;border:1px solid #dee2e6'><b>{}</b></td></tr>"
            "<tr><td style='padding:8px;border:1px solid #dee2e6'>🔧 Standardised values</td>"
            "    <td style='padding:8px;border:1px solid #dee2e6'><b>{}</b></td></tr>"
            "</table>",
            obj.rows_total, obj.rows_imported,
            obj.rows_duplicates, obj.rows_missing, obj.rows_standardized,
        )
    cleaning_report_display.short_description = "Cleaning Report"

    def export_links(self, obj):
        if obj.status != "done":
            return "—"
        base = reverse("admin:voting_datasetimport_export", args=[obj.pk])
        return format_html(
            '<a href="{}?fmt=csv" style="margin-right:6px">⬇ CSV</a>'
            '<a href="{}?fmt=json">⬇ JSON</a>',
            base, base,
        )
    export_links.short_description = "Export result"

    # ── Custom URL for per-import export ────────────────────────────────────

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:pk>/export/",
                self.admin_site.admin_view(self.export_result_view),
                name="voting_datasetimport_export",
            ),
            path(
                "export-all/users/csv/",
                self.admin_site.admin_view(self.export_all_users_csv),
                name="voting_datasetimport_export_users_csv",
            ),
            path(
                "export-all/users/json/",
                self.admin_site.admin_view(self.export_all_users_json),
                name="voting_datasetimport_export_users_json",
            ),
            path(
                "export-all/ballots/csv/",
                self.admin_site.admin_view(self.export_all_ballots_csv),
                name="voting_datasetimport_export_ballots_csv",
            ),
            path(
                "export-all/ballots/json/",
                self.admin_site.admin_view(self.export_all_ballots_json),
                name="voting_datasetimport_export_ballots_json",
            ),
        ]
        return custom + urls

    def export_result_view(self, request, pk):
        """Export the records that belong to this import's target model."""
        obj = DatasetImport.objects.get(pk=pk)
        fmt = request.GET.get("fmt", "csv")
        if obj.target_model == "users":
            return export_users_csv() if fmt == "csv" else export_users_json()
        return export_ballots_csv() if fmt == "csv" else export_ballots_json()

    def export_all_users_csv(self, request):
        return export_users_csv()

    def export_all_users_json(self, request):
        return export_users_json()

    def export_all_ballots_csv(self, request):
        return export_ballots_csv()

    def export_all_ballots_json(self, request):
        return export_ballots_json()

    # ── Override save to run the cleaning + import pipeline ─────────────────

    def save_model(self, request, obj, form, change):
        """
        On first save (change=False) run the full pipeline:
          1. Parse file (CSV or JSON)
          2. Clean rows (dedup, missing-values, format standardisation)
          3. Import into target model
          4. Persist stats on the DatasetImport record
        """
        if change:
            super().save_model(request, obj, form, change)
            return

        obj.imported_by = request.user
        obj.status      = "processing"
        super().save_model(request, obj, form, change)

        try:
            # 1. Parse
            obj.file.seek(0)
            raw_rows = parse_uploaded_file(obj.file)

            # 2. Clean
            if obj.target_model == "users":
                cleaned, stats = clean_user_rows(raw_rows)
            else:
                cleaned, stats = clean_ballot_rows(raw_rows)

            obj.rows_total        = stats["rows_total"]
            obj.rows_duplicates   = stats["rows_duplicates"]
            obj.rows_missing      = stats["rows_missing"]
            obj.rows_standardized = stats["rows_standardized"]

            # 3. Import
            if obj.target_model == "users":
                result = import_users(cleaned)
            else:
                result = import_ballots(cleaned)

            obj.rows_imported = result["created"] + result["updated"]
            obj.error_log     = "\n".join(result.get("errors", []))
            obj.status        = "done"

            messages.success(
                request,
                f"✅ Import complete: {result['created']} created, "
                f"{result['updated']} updated, "
                f"{stats['rows_duplicates']} duplicates removed, "
                f"{stats['rows_missing']} rows skipped (missing required fields), "
                f"{stats['rows_standardized']} values standardised.",
            )

        except Exception as exc:
            obj.status    = "failed"
            obj.error_log = traceback.format_exc()
            messages.error(request, f"❌ Import failed: {exc}")

        finally:
            obj.finished_at = timezone.now()
            obj.save()

    # ── Inject export shortcuts into the changelist top-matter ──────────────

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["export_shortcuts"] = [
            {
                "label": "⬇ Export ALL Users (CSV)",
                "url":   reverse("admin:voting_datasetimport_export_users_csv"),
            },
            {
                "label": "⬇ Export ALL Users (JSON)",
                "url":   reverse("admin:voting_datasetimport_export_users_json"),
            },
            {
                "label": "⬇ Export ALL Ballots (CSV)",
                "url":   reverse("admin:voting_datasetimport_export_ballots_csv"),
            },
            {
                "label": "⬇ Export ALL Ballots (JSON)",
                "url":   reverse("admin:voting_datasetimport_export_ballots_json"),
            },
        ]
        return super().changelist_view(request, extra_context=extra_context)


# ══════════════════════════════════════════════════════════════════════════════
#  Finance (Epic SCRUM-21) — income/expense tracking & budgets
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "type", "amount", "category", "description", "user", "created_at")
    list_filter = ("type", "category", "date")
    search_fields = ("description", "category", "user__username", "user__email")
    date_hierarchy = "date"
    ordering = ("-date", "-created_at")


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("category", "monthly_limit", "user")
    list_filter = ("category",)
    search_fields = ("category", "user__username", "user__email")


# ══════════════════════════════════════════════════════════════════════════════
#  Smart Notifications (Epic SCRUM-20) — announcements & FAQ chatbot
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "msg_type", "audience", "created_by", "recipient_count", "created_at")
    list_filter = ("msg_type", "audience", "created_at")
    search_fields = ("title", "body")
    ordering = ("-created_at",)


@admin.register(AnnouncementRecipient)
class AnnouncementRecipientAdmin(admin.ModelAdmin):
    list_display = ("announcement", "user", "is_read", "read_at")
    list_filter = ("is_read",)
    search_fields = ("announcement__title", "user__username", "user__email")


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "keywords", "created_at")
    search_fields = ("question", "answer", "keywords")
    ordering = ("-created_at",)
