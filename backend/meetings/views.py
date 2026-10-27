from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Meeting, MeetingParticipant, MeetingArchive
from .serializers import (
    MeetingListSerializer,
    MeetingDetailSerializer,
    MeetingArchiveSerializer,
)


# ─── Auth helpers ─────────────────────────────────────────────────────────────
# This app authenticates with a custom session key ("user_id") set by
# voting.views.login_view — it does NOT call Django's login(), so
# request.user is always AnonymousUser. These helpers read the session
# instead, matching the rest of the app (voting.views.is_admin).

def get_session_user(request):
    """Return the logged-in User (via session) or None."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None


def require_login(request):
    """Returns a 401 Response if the user is not logged in, else None."""
    if get_session_user(request) is None:
        return Response({"error": "Login required."}, status=status.HTTP_401_UNAUTHORIZED)
    return None


def require_admin(request):
    """Returns a 403 Response if the user is not staff/admin, else None."""
    user = get_session_user(request)
    if user is None:
        return Response({"error": "Login required."}, status=status.HTTP_401_UNAUTHORIZED)
    if not (user.is_staff or user.is_superuser):
        return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
    return None


# ─── Notification helpers ──────────────────────────────────────────────────────

def send_email_notification(participant: MeetingParticipant, meeting: Meeting):
    """
    Send a plain-text email invite.
    Uses Django's built-in send_mail — configure EMAIL_* in settings.py.
    """
    subject = f"📅 Meeting Invitation: {meeting.title}"
    body = (
        f"Hi {participant.name},\n\n"
        f"You have been invited to the following meeting:\n\n"
        f"  Title:    {meeting.title}\n"
        f"  When:     {meeting.scheduled_at:%A, %B %d %Y at %H:%M UTC}\n"
        f"  Duration: {meeting.duration_minutes} minutes\n"
        f"  Where:    {meeting.location or 'TBD'}\n\n"
        f"{('Details: ' + meeting.description + chr(10)) if meeting.description else ''}"
        f"\nSee you there!"
    )
    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@portal.app"),
        recipient_list=[participant.email],
        fail_silently=False,
    )


def send_whatsapp_notification(participant: MeetingParticipant, meeting: Meeting):
    """
    Send a WhatsApp message via Twilio.
    Requires: pip install twilio
    Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM in settings.py
    """
    try:
        from twilio.rest import Client
    except ImportError:
        raise RuntimeError("Twilio is not installed. Run: pip install twilio")

    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
    auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
    from_number = getattr(settings, "TWILIO_WHATSAPP_FROM", "")  # e.g. "whatsapp:+14155238886"

    if not all([account_sid, auth_token, from_number]):
        raise RuntimeError(
            "Twilio credentials not configured. "
            "Add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM to settings.py"
        )

    message_body = (
        f"📅 *Meeting Invitation*\n\n"
        f"*{meeting.title}*\n"
        f"🗓 {meeting.scheduled_at:%A, %B %d %Y at %H:%M UTC}\n"
        f"⏱ {meeting.duration_minutes} minutes\n"
        f"📍 {meeting.location or 'TBD'}\n\n"
        f"Hi {participant.name}, you're invited!"
    )

    client = Client(account_sid, auth_token)
    client.messages.create(
        body=message_body,
        from_=from_number,
        to=f"whatsapp:{participant.phone}",
    )


def notify_participant(participant: MeetingParticipant, meeting: Meeting):
    """
    Dispatch notifications to a single participant based on their chosen channel.
    Saves the result (success time or error) back to the participant record.
    """
    errors = []

    # Email
    if participant.notification_channel in (
        MeetingParticipant.CHANNEL_EMAIL,
        MeetingParticipant.CHANNEL_BOTH,
    ):
        if participant.email:
            try:
                send_email_notification(participant, meeting)
            except Exception as exc:
                errors.append(f"Email: {exc}")
        else:
            errors.append("Email: no address provided")

    # WhatsApp
    if participant.notification_channel in (
        MeetingParticipant.CHANNEL_WHATSAPP,
        MeetingParticipant.CHANNEL_BOTH,
    ):
        if participant.phone:
            try:
                send_whatsapp_notification(participant, meeting)
            except Exception as exc:
                errors.append(f"WhatsApp: {exc}")
        else:
            errors.append("WhatsApp: no phone number provided")

    if errors:
        participant.notification_error = "; ".join(errors)
    else:
        participant.notified_at = timezone.now()
        participant.notification_error = ""

    participant.save(update_fields=["notified_at", "notification_error"])


# ─── Meeting list & create ─────────────────────────────────────────────────────

class MeetingListView(APIView):
    """
    GET  /api/meetings/         → list all meetings (any logged-in user)
    POST /api/meetings/         → create a new meeting (admin only)
    """

    def get(self, request):
        guard = require_login(request)
        if guard:
            return guard

        meetings = Meeting.objects.select_related("created_by").prefetch_related(
            "participants"
        )
        serializer = MeetingListSerializer(meetings, many=True)
        return Response(serializer.data)

    def post(self, request):
        guard = require_admin(request)
        if guard:
            return guard

        serializer = MeetingDetailSerializer(data=request.data)
        if serializer.is_valid():
            meeting = serializer.save(created_by=get_session_user(request))
            return Response(
                MeetingDetailSerializer(meeting).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─── Single meeting CRUD ───────────────────────────────────────────────────────

class MeetingDetailView(APIView):
    """
    GET    /api/meetings/<id>/   → retrieve a meeting
    PATCH  /api/meetings/<id>/   → update (admin only)
    DELETE /api/meetings/<id>/   → delete (admin only)
    """

    def _get_meeting(self, pk):
        try:
            return Meeting.objects.prefetch_related("participants").select_related(
                "created_by", "archive"
            ).get(pk=pk)
        except Meeting.DoesNotExist:
            return None

    def get(self, request, pk):
        guard = require_login(request)
        if guard:
            return guard

        meeting = self._get_meeting(pk)
        if not meeting:
            return Response({"error": "Meeting not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = MeetingDetailSerializer(meeting, context={"request": request})
        return Response(serializer.data)

    def patch(self, request, pk):
        guard = require_admin(request)
        if guard:
            return guard

        meeting = self._get_meeting(pk)
        if not meeting:
            return Response({"error": "Meeting not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = MeetingDetailSerializer(meeting, data=request.data, partial=True)
        if serializer.is_valid():
            updated = serializer.save()
            return Response(MeetingDetailSerializer(updated, context={"request": request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        guard = require_admin(request)
        if guard:
            return guard

        meeting = self._get_meeting(pk)
        if not meeting:
            return Response({"error": "Meeting not found."}, status=status.HTTP_404_NOT_FOUND)

        meeting.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Notify participants ───────────────────────────────────────────────────────

class MeetingNotifyView(APIView):
    """
    POST /api/meetings/<id>/notify/
    Triggers notifications to all participants of the given meeting.
    Admin only. Returns per-participant success/error info.
    """

    def post(self, request, pk):
        guard = require_admin(request)
        if guard:
            return guard

        try:
            meeting = Meeting.objects.prefetch_related("participants").get(pk=pk)
        except Meeting.DoesNotExist:
            return Response({"error": "Meeting not found."}, status=status.HTTP_404_NOT_FOUND)

        results = []
        for participant in meeting.participants.all():
            notify_participant(participant, meeting)
            results.append({
                "participant": participant.name,
                "email": participant.email,
                "channel": participant.notification_channel,
                "success": bool(participant.notified_at and not participant.notification_error),
                "error": participant.notification_error or None,
            })

        return Response({"meeting": meeting.title, "results": results})


# ─── Archive a completed meeting ───────────────────────────────────────────────

class MeetingArchiveView(APIView):
    """
    POST  /api/meetings/<id>/archive/   → upload video and/or transcript (admin only)
    GET   /api/meetings/<id>/archive/   → retrieve archive details
    """

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, pk):
        guard = require_login(request)
        if guard:
            return guard

        try:
            meeting = Meeting.objects.get(pk=pk)
        except Meeting.DoesNotExist:
            return Response({"error": "Meeting not found."}, status=status.HTTP_404_NOT_FOUND)

        if not hasattr(meeting, "archive"):
            return Response({"error": "This meeting has no archive yet."}, status=status.HTTP_404_NOT_FOUND)

        serializer = MeetingArchiveSerializer(meeting.archive, context={"request": request})
        return Response(serializer.data)

    def post(self, request, pk):
        guard = require_admin(request)
        if guard:
            return guard

        try:
            meeting = Meeting.objects.get(pk=pk)
        except Meeting.DoesNotExist:
            return Response({"error": "Meeting not found."}, status=status.HTTP_404_NOT_FOUND)

        # If an archive already exists, update it instead of creating a duplicate
        archive = getattr(meeting, "archive", None)
        serializer = MeetingArchiveSerializer(
            archive, data=request.data, partial=bool(archive), context={"request": request}
        )

        if serializer.is_valid():
            saved = serializer.save(meeting=meeting, archived_by=get_session_user(request))
            # Automatically move the meeting status to "done"
            meeting.status = Meeting.STATUS_DONE
            meeting.save(update_fields=["status"])
            return Response(
                MeetingArchiveSerializer(saved, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
