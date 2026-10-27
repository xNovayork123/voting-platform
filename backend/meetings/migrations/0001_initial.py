from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Meeting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("location", models.CharField(blank=True, help_text="Room name, or a video call link", max_length=255)),
                ("scheduled_at", models.DateTimeField()),
                ("duration_minutes", models.PositiveIntegerField(default=60)),
                ("status", models.CharField(
                    choices=[
                        ("scheduled", "Scheduled"),
                        ("in_progress", "In Progress"),
                        ("done", "Done"),
                        ("cancelled", "Cancelled"),
                    ],
                    default="scheduled",
                    max_length=20,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="created_meetings",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["-scheduled_at"]},
        ),
        migrations.CreateModel(
            name="MeetingParticipant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("email", models.EmailField(blank=True)),
                ("phone", models.CharField(blank=True, help_text="International format, e.g. +491701234567", max_length=20)),
                ("notification_channel", models.CharField(
                    choices=[
                        ("email", "Email only"),
                        ("whatsapp", "WhatsApp only"),
                        ("both", "Email + WhatsApp"),
                    ],
                    default="email",
                    max_length=10,
                )),
                ("notified_at", models.DateTimeField(blank=True, null=True)),
                ("notification_error", models.TextField(blank=True)),
                ("meeting", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="participants",
                    to="meetings.meeting",
                )),
            ],
            options={"unique_together": {("meeting", "email")}},
        ),
        migrations.CreateModel(
            name="MeetingArchive",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("archive_type", models.CharField(
                    choices=[
                        ("video", "Video only"),
                        ("transcript", "Transcript only"),
                        ("both", "Video + Transcript"),
                    ],
                    max_length=15,
                )),
                ("video_file", models.FileField(blank=True, null=True, upload_to="meetings/videos/")),
                ("transcript_file", models.FileField(blank=True, null=True, upload_to="meetings/transcripts/")),
                ("notes", models.TextField(blank=True, help_text="Official meeting minutes or summary")),
                ("archived_at", models.DateTimeField(auto_now_add=True)),
                ("archived_by", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="archived_meetings",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("meeting", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="archive",
                    to="meetings.meeting",
                )),
            ],
        ),
    ]
