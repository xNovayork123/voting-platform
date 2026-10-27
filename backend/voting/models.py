from django.db import models
from django.contrib.auth.models import User
import uuid


class Ballot(models.Model):
    STATUS_CHOICES = [("open", "Open"), ("closed", "Closed")]
    CATEGORY_CHOICES = [
        ("general", "General"),
        ("music", "Music"),
        ("gaming", "Gaming"),
        ("sports", "Sports"),
        ("technology", "Technology"),
        ("food", "Food"),
        ("travel", "Travel"),
        ("movies", "Movies"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    options = models.JSONField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="general")
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='docvault/')
    category = models.CharField(max_length=100, default='General')
    tags = models.CharField(max_length=255, blank=True)
    size = models.BigIntegerField()
    icon = models.CharField(max_length=10)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='uploaded_documents'
    )

    def __str__(self):
        return self.name


class Vote(models.Model):
    ballot = models.ForeignKey(Ballot, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="votes",
        null=True, blank=True
    )
    option = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Vote for '{self.option}' on ballot {self.ballot_id}"


class UserProfile(models.Model):
    """
    Extiende el User nativo de Django (username/email/password/is_staff/...)
    sin modificarlo: relación uno-a-uno con los campos extra que la UI de
    perfil y de administración de usuarios necesita.
    """
    STATUS_CHOICES = [('online', 'Online'), ('offline', 'Offline')]

    # related_name='profile' -> permite escribir "user.profile" desde cualquier vista.
    # on_delete=CASCADE -> si se borra el User, se borra su perfil con él.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='offline')

    # Se guarda como string base64 (data:image/...;base64,...) directo en la
    # base de datos, no como archivo en MEDIA_ROOT. Simple de implementar,
    # pero no escala: cada fila de /admin/users/ trae la imagen completa.
    profile_picture = models.TextField(blank=True, null=True)  # base64 data URL

    # Nombre visible en la UI; puede ser distinto del username (que es el email).
    display_name = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return f"Profile of {self.user.email}"


class BallotSuggestion(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    options = models.JSONField()
    suggested_by = models.CharField(max_length=255)  # username/email
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    admin_note = models.TextField(blank=True)

    def __str__(self):
        return f"Suggestion: {self.title} by {self.suggested_by}"


# ─── Dataset Import / Export ──────────────────────────────────────────────────

class DatasetImport(models.Model):
    """Tracks every dataset file imported through the Django admin."""

    STATUS_CHOICES = [
        ("pending",    "Pending"),
        ("processing", "Processing"),
        ("done",       "Done"),
        ("failed",     "Failed"),
    ]

    TARGET_CHOICES = [
        ("users",    "Users"),
        ("ballots",  "Ballots"),
    ]

    file = models.FileField(upload_to="dataset_imports/")
    target_model = models.CharField(max_length=20, choices=TARGET_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="pending")

    # Cleaning statistics (filled in after processing)
    rows_total       = models.IntegerField(default=0)
    rows_imported    = models.IntegerField(default=0)
    rows_duplicates  = models.IntegerField(default=0)
    rows_missing     = models.IntegerField(default=0)
    rows_standardized = models.IntegerField(default=0)

    error_log  = models.TextField(blank=True)
    notes      = models.TextField(blank=True, help_text="Optional notes about this import")

    imported_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="dataset_imports"
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Dataset Import"
        verbose_name_plural = "Dataset Imports"

    def __str__(self):
        return f"[{self.get_target_model_display()}] {self.file.name} – {self.get_status_display()}"


# ─── Smart Notifications & Automated Replies (Epic SCRUM-20) ──────────────────

class Announcement(models.Model):
    """
    SCRUM-62: A platform-wide message or reminder created by an admin.
    SCRUM-63: Delivered to all members, or to a specified group of members.
    """
    TYPE_ANNOUNCEMENT = "announcement"
    TYPE_REMINDER = "reminder"
    TYPE_CHOICES = [
        (TYPE_ANNOUNCEMENT, "Announcement"),
        (TYPE_REMINDER, "Reminder"),
    ]

    # SCRUM-63: target everyone, or a specified group of members.
    AUDIENCE_ALL = "all"
    AUDIENCE_ADMINS = "admins"
    AUDIENCE_MEMBERS = "members"
    AUDIENCE_CHOICES = [
        (AUDIENCE_ALL, "All members"),
        (AUDIENCE_ADMINS, "Admins / staff only"),
        (AUDIENCE_MEMBERS, "Members only (non-admin)"),
    ]

    title = models.CharField(max_length=255)
    body = models.TextField()
    msg_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_ANNOUNCEMENT)
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default=AUDIENCE_ALL)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="announcements"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def recipient_count(self):
        return self.recipients.count()

    def __str__(self):
        return f"[{self.get_msg_type_display()}] {self.title}"


class AnnouncementRecipient(models.Model):
    """
    SCRUM-63: One delivered copy of an announcement to a single member.
    Powers the in-app inbox and the unread badge.
    """
    announcement = models.ForeignKey(
        Announcement, on_delete=models.CASCADE, related_name="recipients"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="received_announcements"
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("announcement", "user")
        ordering = ["-announcement__created_at"]

    def __str__(self):
        return f"{self.announcement.title} -> {self.user.username}"


class FAQ(models.Model):
    """
    SCRUM-28: A question/answer pair the FAQ chatbot uses to answer
    members' frequently-asked questions.
    """
    question = models.CharField(max_length=500)
    answer = models.TextField()
    keywords = models.CharField(
        max_length=500, blank=True,
        help_text="Comma-separated keywords to help match this FAQ."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.question


# ─── Finance: Income/Expense Tracking & Budgets (Epic SCRUM-21) ───────────────

class Transaction(models.Model):
    TYPE_CHOICES = [("income", "Income"), ("expense", "Expense")]

    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=100, default="General")
    description = models.CharField(max_length=255, blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="transactions", null=True, blank=True
    )
    # Optional receipt / invoice file attached to this transaction
    receipt = models.FileField(upload_to='receipts/', null=True, blank=True)

    def __str__(self):
        return f"{self.type} - {self.amount} ({self.category})"


class Budget(models.Model):
    # Monthly spending limit per category (for the budget warning feature)
    category = models.CharField(max_length=100)
    monthly_limit = models.DecimalField(max_digits=12, decimal_places=2)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="budgets", null=True, blank=True
    )

    def __str__(self):
        return f"{self.category}: {self.monthly_limit}"
