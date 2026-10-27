from rest_framework import serializers
from .models import Meeting, MeetingParticipant, MeetingArchive


class MeetingParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingParticipant
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "notification_channel",
            "notified_at",
            "notification_error",
        ]


class MeetingArchiveSerializer(serializers.ModelSerializer):
    # Return a usable URL for uploaded files instead of a raw path
    video_url = serializers.SerializerMethodField()
    transcript_url = serializers.SerializerMethodField()

    class Meta:
        model = MeetingArchive
        fields = [
            "id",
            "archive_type",
            "video_file",
            "video_url",
            "transcript_file",
            "transcript_url",
            "notes",
            "archived_at",
        ]
        read_only_fields = ["archived_at"]

    def get_video_url(self, obj):
        if obj.video_file:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.video_file.url) if request else obj.video_file.url
        return None

    def get_transcript_url(self, obj):
        if obj.transcript_file:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.transcript_file.url) if request else obj.transcript_file.url
        return None


class MeetingListSerializer(serializers.ModelSerializer):
    """Lightweight serializer used for the meeting list view."""
    participant_count = serializers.SerializerMethodField()
    has_archive = serializers.SerializerMethodField()
    created_by_username = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = [
            "id",
            "title",
            "description",
            "location",
            "scheduled_at",
            "duration_minutes",
            "status",
            "participant_count",
            "has_archive",
            "created_by_username",
            "created_at",
        ]

    def get_participant_count(self, obj):
        return obj.participants.count()

    def get_has_archive(self, obj):
        return hasattr(obj, "archive")

    def get_created_by_username(self, obj):
        return obj.created_by.username if obj.created_by else "Unknown"


class MeetingDetailSerializer(serializers.ModelSerializer):
    """Full serializer used for create / retrieve / update."""
    participants = MeetingParticipantSerializer(many=True, required=False)
    archive = MeetingArchiveSerializer(read_only=True)
    created_by_username = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = [
            "id",
            "title",
            "description",
            "location",
            "scheduled_at",
            "duration_minutes",
            "status",
            "participants",
            "archive",
            "created_by_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "archive"]

    def get_created_by_username(self, obj):
        return obj.created_by.username if obj.created_by else "Unknown"

    def create(self, validated_data):
        # Pull out nested participants list before creating the meeting
        participants_data = validated_data.pop("participants", [])
        meeting = Meeting.objects.create(**validated_data)

        for participant in participants_data:
            MeetingParticipant.objects.create(meeting=meeting, **participant)

        return meeting

    def update(self, instance, validated_data):
        # If participants are included in an update, replace the whole list
        participants_data = validated_data.pop("participants", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if participants_data is not None:
            instance.participants.all().delete()
            for participant in participants_data:
                MeetingParticipant.objects.create(meeting=instance, **participant)

        return instance
