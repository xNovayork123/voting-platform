from rest_framework import serializers
from .models import Ballot, Vote, BallotSuggestion, Announcement, AnnouncementRecipient, FAQ


class BallotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ballot
        fields = ["id", "title", "description", "options", "category", "start_date", "end_date", "status", "created_at"]

    def validate_options(self, value):
        if not isinstance(value, list) or len(value) < 2:
            raise serializers.ValidationError("En az 2 seçenek girilmelidir.")
        for opt in value:
            if not isinstance(opt, str) or not opt.strip():
                raise serializers.ValidationError("Seçenekler boş olamaz.")
        return value

    def validate(self, data):
        start = data.get("start_date")
        end = data.get("end_date")
        if start and end and end <= start:
            raise serializers.ValidationError("Bitiş tarihi başlangıç tarihinden sonra olmalıdır.")
        return data


class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ["option"]

    def validate_option(self, value):
        ballot = self.context["ballot"]
        if value not in ballot.options:
            raise serializers.ValidationError("Geçersiz seçenek.")
        return value


class BallotSuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BallotSuggestion
        fields = ["id", "title", "description", "options", "suggested_by", "status", "created_at", "admin_note"]
        read_only_fields = ["suggested_by", "status", "created_at", "admin_note"]

    def validate_options(self, value):
        if not isinstance(value, list) or len(value) < 2:
            raise serializers.ValidationError("En az 2 seçenek girilmelidir.")
        return value


class AnnouncementSerializer(serializers.ModelSerializer):
    """SCRUM-62/63: admin-facing view of a created announcement."""
    created_by_email = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [
            "id", "title", "body", "msg_type", "audience",
            "created_by_email", "recipient_count", "created_at",
        ]
        read_only_fields = ["created_by_email", "recipient_count", "created_at"]

    def get_created_by_email(self, obj):
        return obj.created_by.email if obj.created_by else None

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value

    def validate_body(self, value):
        if not value.strip():
            raise serializers.ValidationError("Message body cannot be empty.")
        return value


class InboxItemSerializer(serializers.ModelSerializer):
    """SCRUM-63: a single delivered message in a member's in-app inbox."""
    id = serializers.IntegerField(source="announcement.id", read_only=True)
    title = serializers.CharField(source="announcement.title", read_only=True)
    body = serializers.CharField(source="announcement.body", read_only=True)
    msg_type = serializers.CharField(source="announcement.msg_type", read_only=True)
    created_at = serializers.DateTimeField(source="announcement.created_at", read_only=True)

    class Meta:
        model = AnnouncementRecipient
        fields = ["id", "title", "body", "msg_type", "is_read", "read_at", "created_at"]


class FAQSerializer(serializers.ModelSerializer):
    """SCRUM-28: stored Q&A pairs the chatbot answers from."""
    class Meta:
        model = FAQ
        fields = ["id", "question", "answer", "keywords", "created_at"]
        read_only_fields = ["created_at"]
