from django.contrib import admin
from .models import Meeting, MeetingParticipant, MeetingArchive


class MeetingParticipantInline(admin.TabularInline):
    model = MeetingParticipant
    extra = 1
    fields = ("name", "email", "phone", "notification_channel", "notified_at", "notification_error")
    readonly_fields = ("notified_at", "notification_error")


class MeetingArchiveInline(admin.StackedInline):
    model = MeetingArchive
    extra = 0
    fields = ("archive_type", "video_file", "transcript_file", "notes", "archived_at")
    readonly_fields = ("archived_at",)


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ("title", "scheduled_at", "duration_minutes", "status", "created_by", "participant_count")
    list_filter = ("status",)
    search_fields = ("title", "description", "location")
    inlines = [MeetingParticipantInline, MeetingArchiveInline]

    def participant_count(self, obj):
        return obj.participants.count()
    participant_count.short_description = "Participants"


@admin.register(MeetingParticipant)
class MeetingParticipantAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "notification_channel", "meeting", "notified_at")
    list_filter = ("notification_channel",)
    search_fields = ("name", "email")


@admin.register(MeetingArchive)
class MeetingArchiveAdmin(admin.ModelAdmin):
    list_display = ("meeting", "archive_type", "archived_at", "archived_by")
    readonly_fields = ("archived_at",)
