from django.urls import path
from . import views

urlpatterns = [
    # List all meetings / create a new one
    path("meetings/", views.MeetingListView.as_view(), name="meeting-list"),

    # Retrieve / update / delete a single meeting
    path("meetings/<int:pk>/", views.MeetingDetailView.as_view(), name="meeting-detail"),

    # Send notifications to all participants
    path("meetings/<int:pk>/notify/", views.MeetingNotifyView.as_view(), name="meeting-notify"),

    # Upload or retrieve the post-meeting archive
    path("meetings/<int:pk>/archive/", views.MeetingArchiveView.as_view(), name="meeting-archive"),
]
