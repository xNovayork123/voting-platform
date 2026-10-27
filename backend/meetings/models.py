from django.db import models
from django.contrib.auth.models import User


class Meeting(models.Model):
    """
    Represents a scheduled meeting in the portal.
    Tracks lifecycle from scheduling → in-progress → archived.
    """

    STATUS_SCHEDULED = "scheduled"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_DONE = "done"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_DONE, "Done"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True, help_text="Room name, or a video call link")
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_meetings"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_at"]

    def __str__(self):
        return f"{self.title} ({self.scheduled_at:%Y-%m-%d %H:%M})"


class MeetingParticipant(models.Model):
    """
    A person invited to a meeting.
    May or may not be a registered user — identified by email.
    """

    CHANNEL_EMAIL = "email"
    CHANNEL_WHATSAPP = "whatsapp"
    CHANNEL_BOTH = "both"

    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, "Email only"),
        (CHANNEL_WHATSAPP, "WhatsApp only"),
        (CHANNEL_BOTH, "Email + WhatsApp"),
    ]

    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name="participants")
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(
        max_length=20, blank=True, help_text="International format, e.g. +491701234567"
    )
    notification_channel = models.CharField(
        max_length=10, choices=CHANNEL_CHOICES, default=CHANNEL_EMAIL
    )
    # Track whether we successfully sent the notification
    notified_at = models.DateTimeField(null=True, blank=True)
    notification_error = models.TextField(blank=True)

    class Meta:
        unique_together = ("meeting", "email")

    def __str__(self):
        return f"{self.name} <{self.email}> @ {self.meeting.title}"


class MeetingArchive(models.Model):
    """
    Stores the post-meeting materials: video recording and/or transcript.
    One meeting can have one archive entry.
    """

    ARCHIVE_TYPE_VIDEO = "video"
    ARCHIVE_TYPE_TRANSCRIPT = "transcript"
    ARCHIVE_TYPE_BOTH = "both"

    ARCHIVE_TYPE_CHOICES = [
        (ARCHIVE_TYPE_VIDEO, "Video only"),
        (ARCHIVE_TYPE_TRANSCRIPT, "Transcript only"),
        (ARCHIVE_TYPE_BOTH, "Video + Transcript"),
    ]

    meeting = models.OneToOneField(Meeting, on_delete=models.CASCADE, related_name="archive")
    archive_type = models.CharField(max_length=15, choices=ARCHIVE_TYPE_CHOICES)
    video_file = models.FileField(
        upload_to="meetings/videos/", null=True, blank=True
    )
    transcript_file = models.FileField(
        upload_to="meetings/transcripts/", null=True, blank=True
    )
    notes = models.TextField(blank=True, help_text="Official meeting minutes or summary")
    archived_at = models.DateTimeField(auto_now_add=True)
    archived_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="archived_meetings"
    )

    def __str__(self):
        return f"Archive for: {self.meeting.title}"
