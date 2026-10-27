import os
from django.utils import timezone
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Document

from .models import Ballot, Vote, BallotSuggestion, Document, UserProfile
from .serializers import BallotSerializer, VoteSerializer, BallotSuggestionSerializer


def is_admin(request):
    # Usado por admin_user_list/admin_user_update (y por otros endpoints admin-only
    # del archivo). "admin" = is_staff OR is_superuser; no es un modelo de roles
    # separado, son los 2 flags que ya trae el User de Django.
    user_id = request.session.get("user_id")
    if not user_id:
        return False
    try:
        from django.contrib.auth.models import User
        user = User.objects.get(pk=user_id)
        return user.is_staff or user.is_superuser
    except Exception:
        return False


@api_view(["GET", "POST"])
def ballot_list(request):
    if request.method == "GET":
        ballots = Ballot.objects.all().order_by("-created_at")
        serializer = BallotSerializer(ballots, many=True)
        return Response(serializer.data)

    # POST - sadece admin
    if not is_admin(request):
        return Response({"error": "Only admins can create ballots."}, status=status.HTTP_403_FORBIDDEN)

    serializer = BallotSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
def ballot_detail(request, pk):
    try:
        ballot = Ballot.objects.get(pk=pk)
    except Ballot.DoesNotExist:
        return Response({"error": "Ballot not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(BallotSerializer(ballot).data)

    # PUT / PATCH / DELETE - admin only
    if not is_admin(request):
        return Response({"error": "Only admins can modify ballots."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "DELETE":
        ballot.delete()
        return Response({"message": "Ballot deleted."}, status=status.HTTP_200_OK)

    partial = request.method == "PATCH"
    serializer = BallotSerializer(ballot, data=request.data, partial=partial)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def cast_vote(request, pk):
    user_id = request.session.get("user_id")
    if not user_id:
        return Response({"error": "You must be logged in to vote."}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        ballot = Ballot.objects.get(pk=pk)
    except Ballot.DoesNotExist:
        return Response({"error": "Ballot not found."}, status=status.HTTP_404_NOT_FOUND)

    if ballot.status == "closed" or timezone.now() > ballot.end_date:
        return Response({"error": "Ballot is closed."}, status=status.HTTP_400_BAD_REQUEST)

    if Vote.objects.filter(ballot=ballot, user_id=user_id).exists():
        return Response({"error": "You have already voted on this ballot."}, status=status.HTTP_400_BAD_REQUEST)

    serializer = VoteSerializer(data=request.data, context={"ballot": ballot})
    if serializer.is_valid():
        serializer.save(ballot=ballot, user_id=user_id)
        return Response({"message": "Your vote has been recorded."}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def my_votes(request):
    """Return the ballots the logged-in user has voted on, with the chosen option."""
    user_id = request.session.get("user_id")
    if not user_id:
        return Response([])

    votes = Vote.objects.filter(user_id=user_id).select_related("ballot").order_by("-timestamp")
    items = [{
        "ballot_id": v.ballot.id,
        "title": v.ballot.title,
        "option": v.option,
        "status": v.ballot.status,
        "end_date": v.ballot.end_date,
    } for v in votes]
    return Response(items)


@api_view(["GET"])
def ballot_results(request, pk):
    try:
        ballot = Ballot.objects.get(pk=pk)
    except Ballot.DoesNotExist:
        return Response({"error": "Ballot not found."}, status=status.HTTP_404_NOT_FOUND)

    votes = Vote.objects.filter(ballot=ballot)
    results = {option: 0 for option in ballot.options}
    for vote in votes:
        if vote.option in results:
            results[vote.option] += 1

    return Response({
        "ballot": ballot.title,
        "status": ballot.status,
        "total_votes": votes.count(),
        "results": results,
    })


@api_view(["POST"])
def login_view(request):
    email = request.data.get("email", "").strip()
    password = request.data.get("password", "")

    if not email or not password:
        return Response({"error": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

    # Look up by email first so imported users can have a username that
    # differs from their email (e.g. via the dataset import feature).
    user_obj = User.objects.filter(email__iexact=email).first()
    if user_obj is None:
        return Response({"error": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED)

    user = authenticate(request, username=user_obj.username, password=password)

    if user is None:
        return Response({"error": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.is_active:
        return Response({"error": "This account has been disabled."}, status=status.HTTP_403_FORBIDDEN)

    request.session["user_id"] = user.id
    request.session["user_email"] = email
    request.session.modified = True

    return Response({
        "message": "Login successful.",
        "user": {
            "id": user.id,
            "email": email,
            "username": user.username,
            "is_admin": user.is_staff or user.is_superuser,
        }
    }, status=status.HTTP_200_OK)


@api_view(["POST"])
def logout_view(request):
    request.session.flush()
    return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)


# --- Öneri (Suggestion) endpoint'leri ---

@api_view(["GET", "POST"])
def suggestion_list(request):
    if request.method == "GET":
        # Sadece admin tüm önerileri görebilir
        if not is_admin(request):
            return Response({"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)
        suggestions = BallotSuggestion.objects.all().order_by("-created_at")
        return Response(BallotSuggestionSerializer(suggestions, many=True).data)

    # POST - giriş yapmış herkes öneri gönderebilir
    user_id = request.session.get("user_id")
    if not user_id:
        return Response({"error": "You must be logged in."}, status=status.HTTP_401_UNAUTHORIZED)

    serializer = BallotSuggestionSerializer(data=request.data)
    if serializer.is_valid():
        email = request.session.get("user_email", "unknown")
        serializer.save(suggested_by=email)
        return Response({"message": "Your suggestion has been submitted for admin review."}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def suggestion_approve(request, pk):
    if not is_admin(request):
        return Response({"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)

    try:
        suggestion = BallotSuggestion.objects.get(pk=pk)
    except BallotSuggestion.DoesNotExist:
        return Response({"error": "Suggestion not found."}, status=status.HTTP_404_NOT_FOUND)

    action = request.data.get("action")  # "approve" or "reject"
    admin_note = request.data.get("admin_note", "")

    if action == "approve":
        suggestion.status = "approved"
        suggestion.admin_note = admin_note
        suggestion.save()
        # Otomatik oylama oluştur
        from django.utils import timezone
        import datetime
        ballot = Ballot.objects.create(
            title=suggestion.title,
            description=suggestion.description,
            options=suggestion.options,
            start_date=timezone.now(),
            end_date=timezone.now() + datetime.timedelta(days=7),
            status="open",
        )
        return Response({"message": "Suggestion approved and ballot created.", "ballot_id": ballot.id})
    elif action == "reject":
        suggestion.status = "rejected"
        suggestion.admin_note = admin_note
        suggestion.save()
        return Response({"message": "Suggestion rejected."})
    else:
        return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def register_view(request):
    email = request.data.get("email", "").strip()
    password = request.data.get("password", "")

    if not email or not password:
        return Response({"error": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

    from django.contrib.auth.models import User
    if User.objects.filter(username=email).exists():
        return Response({"error": "This email is already registered."}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=email, email=email, password=password)

    request.session["user_id"] = user.id
    request.session["user_email"] = email
    request.session.modified = True

    return Response({
        "message": "Registration successful.",
        "user": {
            "id": user.id,
            "email": email,
            "username": user.username,
            "is_admin": False,
        }
    }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def docvault_list(request):
    category = request.GET.get('category', 'All')
    query = request.GET.get('q', '').lower()
    
    docs = Document.objects.all().order_by('-uploaded_at')
    if category and category != 'All':
        docs = docs.filter(category=category)
    if query:
        docs = docs.filter(name__icontains=query)

    # Hardcoded categories for simplicity, matching your Flask setup
    categories = ["General", "Work", "Personal", "Finance", "Archive"]
    
    doc_data = [{
        "id": str(d.id),
        "name": d.name,
        "category": d.category,
        "tags": d.tags,
        "size": d.size,
        "icon": d.icon,
        "uploaded_at": d.uploaded_at.isoformat()
    } for d in docs]
    
    return Response({"documents": doc_data, "categories": categories})

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def docvault_upload(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return Response({"error": "Unauthorized"}, status=401)
        
    file_obj = request.FILES.get('file')
    if not file_obj:
        return Response({"error": "No file provided"}, status=400)

    # Fetch the user object
    user = User.objects.get(id=user_id)

    ext = file_obj.name.split('.')[-1].lower() if '.' in file_obj.name else ''
    icons = { 'pdf': '📄', 'doc': '📝', 'xls': '📊', 'png': '🖼️', 'jpg': '🖼️', 'zip': '📦' }
    icon = icons.get(ext, '📁')

    # Save the user to the document
    doc = Document.objects.create(
        name=file_obj.name,
        file=file_obj,
        category=request.data.get('category', 'General'),
        tags=request.data.get('tags', ''),
        size=file_obj.size,
        icon=icon,
        uploaded_by=user
    )
    return Response({"success": True, "id": str(doc.id)})

@api_view(['DELETE'])
def docvault_delete(request, pk):
    if not request.session.get("user_id"):
        return Response({"error": "Unauthorized"}, status=401)
        
    try:
        doc = Document.objects.get(pk=pk)
        if doc.file:
            if os.path.isfile(doc.file.path):
                os.remove(doc.file.path)
        doc.delete()
        return Response({"success": True})
    except Document.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

@api_view(['GET'])
def docvault_download(request, pk):
    try:
        doc = Document.objects.get(pk=pk)
        response = FileResponse(doc.file.open('rb'), as_attachment=True, filename=doc.name)
        return response
    except Document.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

def _get_profile_data(user):
    """
    Combina User + UserProfile en un solo dict. Se reutiliza en GET/PATCH de
    /profile/. admin_user_list y admin_user_update NO llaman a esta función
    (arman su propio dict inline) -> mismo "shape" repetido en 3 lugares sin
    un Serializer de DRF que lo centralice, hay que mantenerlos sincronizados
    a mano si se agrega/cambia un campo.
    """
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        # Creación perezosa: usuarios creados por Google login, import CSV o
        # "createsuperuser" no pasan por register_view, así que pueden no
        # tener perfil todavía. Se crea aquí en vez de fallar con un 500.
        profile = UserProfile.objects.create(user=user)
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "display_name": profile.display_name or user.username,
        "is_admin": user.is_staff or user.is_superuser,  # no es un campo real, es esta combinación
        "status": profile.status,
        "profile_picture": profile.profile_picture or "",
    }


@api_view(["GET", "PATCH"])
def profile_view(request):
    """GET: devuelve mi propio perfil. PATCH: lo actualiza (edición parcial)."""
    user_id = request.session.get("user_id")
    if not user_id:
        return Response({"error": "Not authenticated."}, status=status.HTTP_401_UNAUTHORIZED)

    user = User.objects.get(pk=user_id)

    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)  # mismo patrón de creación perezosa

    if request.method == "GET":
        return Response(_get_profile_data(user))

    # PATCH parcial: cada campo se toca SOLO si vino en el body. Si usáramos
    # data.get("password", "") a secas, un guardado sin password la vaciaría;
    # por eso el chequeo explícito "in data" en cada campo.
    data = request.data

    if "display_name" in data:
        profile.display_name = data["display_name"].strip()
    if "status" in data and data["status"] in ("online", "offline"):
        profile.status = data["status"]
    if "profile_picture" in data:
        profile.profile_picture = data["profile_picture"]  # ya viene en base64 desde React
    if "email" in data:
        new_email = data["email"].strip()
        if new_email and new_email != user.email:
            # username == email en este proyecto: hay que sincronizar ambos y
            # validar que ningún OTRO usuario ya lo tenga (excluyéndome a mí mismo).
            if User.objects.filter(username=new_email).exclude(pk=user.id).exists():
                return Response({"error": "Email already in use."}, status=status.HTTP_400_BAD_REQUEST)
            user.email = new_email
            user.username = new_email
            request.session["user_email"] = new_email
    if "password" in data and data["password"]:
        user.set_password(data["password"])  # hashea; nunca se asigna user.password = "..." directo
        request.session["user_id"] = user.id

    user.save()
    profile.save()

    return Response(_get_profile_data(user))


@api_view(["GET"])
def admin_user_list(request):
    """Admin-only: lista de TODOS los usuarios con sus datos combinados (User + UserProfile)."""
    if not is_admin(request):
        return Response({"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)

    users = User.objects.all().order_by("id")
    result = []
    for u in users:
        try:
            profile = u.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=u)  # mismo patrón de creación perezosa
        result.append({
            "id": u.id,
            "email": u.email,
            "username": u.username,
            "display_name": profile.display_name or u.username,
            "is_admin": u.is_staff or u.is_superuser,
            "is_active": u.is_active,  # se expone aquí; en mi propio perfil no hace falta mostrármelo
            "status": profile.status,
            "profile_picture": profile.profile_picture or "",
        })
    return Response(result)


@api_view(["PATCH"])
def admin_user_update(request, pk):
    """
    Admin-only: edita a CUALQUIER usuario por id. No existe un DELETE para
    usuarios: dar de baja a alguien se modela como is_active=False (soft
    delete), para no romper sus votos/transacciones/mensajes ya guardados.
    """
    if not is_admin(request):
        return Response({"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)

    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)

    data = request.data

    if "is_admin" in data:
        # is_admin no es un campo real: son is_staff + is_superuser puestos
        # juntos. Solo ESTE endpoint (admin editando a otro) puede tocarlos;
        # profile_view (editar mi propio perfil) nunca acepta este campo, así
        # nadie puede autoasignarse admin por el endpoint equivocado.
        user.is_staff = bool(data["is_admin"])
        user.is_superuser = bool(data["is_admin"])
    if "is_active" in data:
        user.is_active = bool(data["is_active"])  # cuenta desactivada = no puede volver a loguear
    if "display_name" in data:
        profile.display_name = data["display_name"].strip()
    if "email" in data:
        new_email = data["email"].strip()
        if new_email and new_email != user.email:
            if User.objects.filter(username=new_email).exclude(pk=user.id).exists():
                return Response({"error": "Email already in use."}, status=status.HTTP_400_BAD_REQUEST)
            user.email = new_email
            user.username = new_email
    if "password" in data and data["password"]:
        user.set_password(data["password"])  # el admin puede resetear la password de otro usuario

    user.save()
    profile.save()

    return Response({
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "display_name": profile.display_name or user.username,
        "is_admin": user.is_staff or user.is_superuser,
        "is_active": user.is_active,
        "status": profile.status,
        "profile_picture": profile.profile_picture or "",
    })


@api_view(["POST"])
def google_auth_view(request):
    token = request.data.get("token")
    if not token:
        return Response({"error": "Token is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        GOOGLE_CLIENT_ID = '816595047774-00srjbskmn4lkfnr9osl0873utg66h0g.apps.googleusercontent.com'
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)

        email = idinfo.get('email')
        if not email:
            return Response({"error": "Could not get email from Google."}, status=status.HTTP_400_BAD_REQUEST)

        from django.contrib.auth.models import User
        user, created = User.objects.get_or_create(username=email, defaults={'email': email})

        request.session["user_id"] = user.id
        request.session["user_email"] = email
        request.session.modified = True

        return Response({
            "message": "Google sign-in successful.",
            "user": {
                "id": user.id,
                "email": email,
                "username": user.username,
                "is_admin": user.is_staff or user.is_superuser,
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f"Invalid Google token: {str(e)}"}, status=status.HTTP_401_UNAUTHORIZED)


# ─── SCRUM-11: WhatsApp Chat Frequency & Sentiment Analysis ────────────────────
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def analyze_chat(request):
    """
    Analyze a WhatsApp chat export.

    Accepts either an uploaded .txt file (form field "file") or pasted chat
    text (form field "text"). Returns frequency/active-hour metrics (SCRUM-26)
    and VADER sentiment (SCRUM-27). Stateless: nothing is stored.
    """
    # Las 3 funciones puras que hacen el trabajo real -> chat_parser.py,
    # chat_analytics.py y chat_sentiment.py. Esta vista solo orquesta.
    from .chat_parser import parse_chat
    from .chat_analytics import analyze_activity
    from .chat_sentiment import analyze_sentiment

    # Cualquier usuario logueado puede analizar chats (no requiere ser admin).
    if not request.session.get("user_id"):
        return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

    # ── Modo 1: archivo subido, o Modo 2: texto pegado (mutuamente excluyentes) ──
    upload = request.FILES.get("file")
    if upload is not None:
        try:
            raw_text = upload.read().decode("utf-8", errors="ignore")
        except Exception:
            return Response(
                {"error": "Could not read the uploaded file."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    else:
        raw_text = request.data.get("text", "") or ""

    if not raw_text.strip():
        return Response(
            {"error": "Provide a .txt file or paste chat text."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── Pipeline: parsear -> validar -> frecuencia -> sentimiento ──
    messages, parse_stats = parse_chat(raw_text)
    if not messages:
        # El parser corrió pero no reconoció ni un mensaje -> probablemente no
        # es un export real de WhatsApp, o el formato no es el esperado.
        return Response(
            {"error": "No WhatsApp messages found. Check the export format."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    activity = analyze_activity(messages)
    sentiment = analyze_sentiment(messages)

    # Combina los 2 resultados + las stats de parseo en una sola respuesta JSON.
    return Response({
        "summary": activity["summary"],
        "activity_by_hour": activity["activity_by_hour"],
        "peak_hour": activity["peak_hour"],
        "per_participant": activity["per_participant"],
        "sentiment": sentiment["sentiment"],
        "per_participant_sentiment": sentiment["per_participant_sentiment"],
        "parse_stats": parse_stats,
    })


from .models import Announcement, AnnouncementRecipient, FAQ
from .serializers import AnnouncementSerializer, InboxItemSerializer, FAQSerializer


def _current_user(request):
    """Return the logged-in User (via session) or None."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None


# ─── SCRUM-62 & SCRUM-63: Announcements / Reminders ───────────────────────────

@api_view(["GET", "POST"])
def announcement_list(request):
    """
    GET  -> admin: list every announcement that has been sent (with stats).
    POST -> admin: create a new announcement/reminder and deliver it
            to the chosen audience (SCRUM-62 + SCRUM-63).
    """
    if not is_admin(request):
        return Response({"error": "Only admins can manage announcements."},
                        status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        announcements = Announcement.objects.all().order_by("-created_at")
        return Response(AnnouncementSerializer(announcements, many=True).data)

    # POST — create + deliver
    serializer = AnnouncementSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    admin_user = _current_user(request)
    announcement = serializer.save(created_by=admin_user)

    # SCRUM-63: resolve the target audience into a set of recipients.
    audience = announcement.audience
    if audience == Announcement.AUDIENCE_ADMINS:
        targets = User.objects.filter(is_active=True).filter(
            models.Q(is_staff=True) | models.Q(is_superuser=True)
        )
    elif audience == Announcement.AUDIENCE_MEMBERS:
        targets = User.objects.filter(is_active=True, is_staff=False, is_superuser=False)
    else:  # AUDIENCE_ALL
        targets = User.objects.filter(is_active=True)

    # Fan-out: one inbox copy per recipient.
    recipients = [
        AnnouncementRecipient(announcement=announcement, user=u)
        for u in targets
    ]
    AnnouncementRecipient.objects.bulk_create(recipients, ignore_conflicts=True)

    data = AnnouncementSerializer(announcement).data
    data["delivered_to"] = len(recipients)
    return Response(data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def my_inbox(request):
    """
    SCRUM-63 (recipient side): the logged-in member's in-app inbox of
    announcements/reminders that were sent to them.
    """
    user = _current_user(request)
    if not user:
        return Response({"error": "You must be logged in."},
                        status=status.HTTP_401_UNAUTHORIZED)

    items = (AnnouncementRecipient.objects
             .filter(user=user)
             .select_related("announcement")
             .order_by("-announcement__created_at"))
    unread = items.filter(is_read=False).count()
    return Response({
        "unread_count": unread,
        "items": InboxItemSerializer(items, many=True).data,
    })


@api_view(["POST"])
def mark_inbox_read(request, pk):
    """Mark a single inbox message (by announcement id) as read."""
    user = _current_user(request)
    if not user:
        return Response({"error": "You must be logged in."},
                        status=status.HTTP_401_UNAUTHORIZED)
    try:
        rec = AnnouncementRecipient.objects.get(announcement_id=pk, user=user)
    except AnnouncementRecipient.DoesNotExist:
        return Response({"error": "Message not found."}, status=status.HTTP_404_NOT_FOUND)

    if not rec.is_read:
        rec.is_read = True
        rec.read_at = timezone.now()
        rec.save(update_fields=["is_read", "read_at"])
    return Response({"message": "Marked as read."})


# ─── SCRUM-28: FAQ AI chatbot ─────────────────────────────────────────────────

@api_view(["GET", "POST"])
def faq_list(request):
    """
    GET  -> anyone: list all FAQ entries.
    POST -> admin: add a new FAQ entry for the chatbot to answer from.
    """
    if request.method == "GET":
        faqs = FAQ.objects.all().order_by("-created_at")
        return Response(FAQSerializer(faqs, many=True).data)

    if not is_admin(request):
        return Response({"error": "Only admins can add FAQs."},
                        status=status.HTTP_403_FORBIDDEN)

    serializer = FAQSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
def faq_delete(request, pk):
    """Admin: remove an FAQ entry."""
    if not is_admin(request):
        return Response({"error": "Only admins can delete FAQs."},
                        status=status.HTTP_403_FORBIDDEN)
    try:
        FAQ.objects.get(pk=pk).delete()
    except FAQ.DoesNotExist:
        return Response({"error": "FAQ not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response({"message": "FAQ deleted."})


def _score_faq(question, faq):
    """
    Lightweight relevance score between a member's question and an FAQ entry.
    Counts how many of the FAQ's keywords / question words appear in the input.
    """
    q = question.lower()
    score = 0

    # Keyword matches are weighted highest.
    for kw in (k.strip().lower() for k in faq.keywords.split(",") if k.strip()):
        if kw and kw in q:
            score += 3

    # Fall back to overlap with the FAQ's own question wording.
    import re
    stop = {"the", "a", "an", "is", "are", "do", "i", "to", "how", "what",
            "can", "of", "in", "on", "for", "my", "me", "you", "and", "or"}
    faq_words = {w for w in re.findall(r"[a-z0-9]+", faq.question.lower()) if w not in stop}
    asked_words = {w for w in re.findall(r"[a-z0-9]+", q) if w not in stop}
    score += len(faq_words & asked_words)
    return score


@api_view(["POST"])
def faq_chatbot(request):
    """
    SCRUM-28: AI chatbot endpoint.
    Takes a member's free-text question and returns the best-matching FAQ
    answer, so the bot can "answer FAQs like an AI chatbot".
    """
    question = (request.data.get("question") or "").strip()
    if not question:
        return Response({"error": "Please type a question."},
                        status=status.HTTP_400_BAD_REQUEST)

    faqs = list(FAQ.objects.all())
    if not faqs:
        return Response({
            "answer": "There are no FAQs available yet. Please check back later "
                      "or contact an admin.",
            "matched": False,
        })

    scored = [(faq, _score_faq(question, faq)) for faq in faqs]
    best_faq, best_score = max(scored, key=lambda pair: pair[1])

    if best_score <= 0:
        # No confident match — offer the closest topics instead of guessing.
        suggestions = [f.question for f in faqs[:5]]
        return Response({
            "answer": "I'm not sure about that one yet. Here are some questions "
                      "I can help with:",
            "matched": False,
            "suggestions": suggestions,
        })

    return Response({
        "answer": best_faq.answer,
        "matched": True,
        "matched_question": best_faq.question,
    })


# ===================== FINANCE MODULE (Epic SCRUM-21) =====================

from .models import Transaction, Budget


@api_view(['GET'])
def finance_list(request):
    type_filter = request.GET.get('type', 'all')
    query = request.GET.get('q', '').lower()
    start_date = request.GET.get('start', '')
    end_date = request.GET.get('end', '')

    user = _current_user(request)

    # Her kullanıcı sadece kendi işlemlerini görür
    txns = Transaction.objects.all().order_by('-date', '-created_at')
    if user:
        txns = txns.filter(user=user)

    if type_filter in ('income', 'expense'):
        txns = txns.filter(type=type_filter)
    if query:
        txns = txns.filter(description__icontains=query)
    if start_date:
        txns = txns.filter(date__gte=start_date)
    if end_date:
        txns = txns.filter(date__lte=end_date)

    # Özet HER ZAMAN kullanıcının tüm işlemleri üzerinden (filtreden bağımsız)
    all_txns = Transaction.objects.all()
    if user:
        all_txns = all_txns.filter(user=user)
    total_income = sum(float(t.amount) for t in all_txns if t.type == 'income')
    total_expense = sum(float(t.amount) for t in all_txns if t.type == 'expense')
    balance = total_income - total_expense

    txn_data = [{
        "id": t.id,
        "type": t.type,
        "amount": float(t.amount),
        "category": t.category,
        "description": t.description,
        "date": t.date.isoformat(),
        "receipt": t.receipt.url if t.receipt else None,
    } for t in txns]

    return Response({
        "transactions": txn_data,
        "summary": {"income": total_income, "expense": total_expense, "balance": balance}
    })


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def finance_add(request):
    data = request.data
    txn_type = data.get('type')
    amount = data.get('amount')
    category = data.get('category', 'General')
    description = data.get('description', '')
    date = data.get('date')
    receipt = request.FILES.get('receipt')  # opsiyonel fiş/fatura

    if txn_type not in ('income', 'expense'):
        return Response({"error": "Type must be income or expense."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return Response({"error": "Amount must be a number."}, status=status.HTTP_400_BAD_REQUEST)
    if amount <= 0:
        return Response({"error": "Amount must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST)
    if not date:
        return Response({"error": "Date is required."}, status=status.HTTP_400_BAD_REQUEST)

    user = _current_user(request)
    txn = Transaction.objects.create(
        type=txn_type, amount=amount, category=category,
        description=description, date=date, user=user, receipt=receipt,
    )
    warning = _check_budget(user, category, date)
    return Response({"success": True, "id": txn.id, "warning": warning}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def finance_update(request, pk):
    try:
        txn = Transaction.objects.get(pk=pk)
    except Transaction.DoesNotExist:
        return Response({"error": "Transaction not found."}, status=status.HTTP_404_NOT_FOUND)

    data = request.data
    if data.get('type') in ('income', 'expense'):
        txn.type = data.get('type')
    if 'amount' in data:
        try:
            amt = float(data.get('amount'))
            if amt <= 0:
                return Response({"error": "Amount must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST)
            txn.amount = amt
        except (TypeError, ValueError):
            return Response({"error": "Amount must be a number."}, status=status.HTTP_400_BAD_REQUEST)
    if 'category' in data:
        txn.category = data.get('category')
    if 'description' in data:
        txn.description = data.get('description')
    if data.get('date'):
        txn.date = data.get('date')
    if request.FILES.get('receipt'):
        txn.receipt = request.FILES.get('receipt')

    txn.save()
    return Response({"success": True})


@api_view(['DELETE'])
def finance_delete(request, pk):
    try:
        txn = Transaction.objects.get(pk=pk)
        txn.delete()
        return Response({"success": True})
    except Transaction.DoesNotExist:
        return Response({"error": "Transaction not found."}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def finance_stats(request):
    """Kategori dağılımı + aylık karşılaştırma için veri döndürür."""
    import datetime
    user = _current_user(request)
    txns = Transaction.objects.all()
    if user:
        txns = txns.filter(user=user)

    category_totals = {}
    for t in txns:
        if t.type == 'expense':
            category_totals[t.category] = category_totals.get(t.category, 0) + float(t.amount)

    today = datetime.date.today()
    this_month = (today.year, today.month)
    last_month = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)

    def month_totals(year, month):
        inc = exp = 0.0
        for t in txns:
            if t.date.year == year and t.date.month == month:
                if t.type == 'income':
                    inc += float(t.amount)
                else:
                    exp += float(t.amount)
        return {"income": inc, "expense": exp}

    return Response({
        "category_totals": category_totals,
        "this_month": month_totals(*this_month),
        "last_month": month_totals(*last_month),
    })


def _check_budget(user, category, date_str):
    """Bu kategoride bu ayki toplam harcama limiti aştıysa uyarı döndür."""
    import datetime
    budget = Budget.objects.filter(category=category)
    if user:
        budget = budget.filter(user=user)
    budget = budget.first()
    if not budget:
        return None
    try:
        d = datetime.date.fromisoformat(str(date_str))
    except Exception:
        d = datetime.date.today()
    qs = Transaction.objects.filter(type='expense', category=category,
                                    date__year=d.year, date__month=d.month)
    if user:
        qs = qs.filter(user=user)
    spent = sum(float(t.amount) for t in qs)
    if spent > float(budget.monthly_limit):
        return f"Budget exceeded! {category}: {spent:.2f} spent this month (limit: {budget.monthly_limit})."
    return None


@api_view(['GET', 'POST'])
def finance_budgets(request):
    user = _current_user(request)
    if request.method == 'POST':
        category = request.data.get('category')
        limit = request.data.get('monthly_limit')
        if not category or limit is None:
            return Response({"error": "Category and monthly_limit are required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            limit = float(limit)
        except (TypeError, ValueError):
            return Response({"error": "Limit must be a number."}, status=status.HTTP_400_BAD_REQUEST)
        # Aynı kategori varsa güncelle, yoksa oluştur
        budget, _ = Budget.objects.get_or_create(category=category, user=user,
                                                  defaults={"monthly_limit": limit})
        budget.monthly_limit = limit
        budget.save()
        return Response({"success": True})

    budgets = Budget.objects.all()
    if user:
        budgets = budgets.filter(user=user)
    data = [{"id": b.id, "category": b.category, "monthly_limit": float(b.monthly_limit)} for b in budgets]
    return Response({"budgets": data})


@api_view(['GET'])
def finance_export(request):
    """İşlemleri CSV olarak indir."""
    import csv
    from django.http import HttpResponse
    user = _current_user(request)
    txns = Transaction.objects.all().order_by('-date')
    if user:
        txns = txns.filter(user=user)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Category', 'Description', 'Amount'])
    for t in txns:
        writer.writerow([t.date, t.type, t.category, t.description, t.amount])
    return response
