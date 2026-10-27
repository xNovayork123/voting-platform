"""
Migration: add DatasetImport model
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("voting", "0002_userprofile"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DatasetImport",
            fields=[
                ("id",                models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file",              models.FileField(upload_to="dataset_imports/")),
                ("target_model",      models.CharField(choices=[("users", "Users"), ("ballots", "Ballots")], max_length=20)),
                ("status",            models.CharField(choices=[("pending", "Pending"), ("processing", "Processing"), ("done", "Done"), ("failed", "Failed")], default="pending", max_length=15)),
                ("rows_total",        models.IntegerField(default=0)),
                ("rows_imported",     models.IntegerField(default=0)),
                ("rows_duplicates",   models.IntegerField(default=0)),
                ("rows_missing",      models.IntegerField(default=0)),
                ("rows_standardized", models.IntegerField(default=0)),
                ("error_log",         models.TextField(blank=True)),
                ("notes",             models.TextField(blank=True, help_text="Optional notes about this import")),
                ("created_at",        models.DateTimeField(auto_now_add=True)),
                ("finished_at",       models.DateTimeField(null=True, blank=True)),
                ("imported_by",       models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="dataset_imports",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name":        "Dataset Import",
                "verbose_name_plural": "Dataset Imports",
                "ordering":            ["-created_at"],
            },
        ),
    ]
