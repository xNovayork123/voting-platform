from django.urls import path
from . import views

urlpatterns = [
    path("ballots/", views.ballot_list, name="ballot-list"),
    path("ballots/<int:pk>/", views.ballot_detail, name="ballot-detail"),
    path("ballots/<int:pk>/vote/", views.cast_vote, name="cast-vote"),
    path("ballots/<int:pk>/results/", views.ballot_results, name="ballot-results"),
    path("my-votes/", views.my_votes, name="my-votes"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("auth/google/", views.google_auth_view, name="google-auth"),
    path("suggestions/", views.suggestion_list, name="suggestion-list"),
    path("suggestions/<int:pk>/action/", views.suggestion_approve, name="suggestion-action"),
    path('docvault/documents/', views.docvault_list),
    path('docvault/upload/', views.docvault_upload),
    path('docvault/documents/<uuid:pk>/', views.docvault_delete),
    path('docvault/download/<uuid:pk>/', views.docvault_download),
    path('profile/', views.profile_view, name='profile'),                              # mi propio perfil: GET/PATCH
    path('admin/users/', views.admin_user_list, name='admin-user-list'),               # admin: listar todos (GET)
    path('admin/users/<int:pk>/', views.admin_user_update, name='admin-user-update'),  # admin: editar a uno (PATCH)
    path('chat/analyze/', views.analyze_chat, name='chat-analyze'),

    # ── Smart Notifications & Automated Replies (Epic SCRUM-20) ──
    path("announcements/", views.announcement_list, name="announcement-list"),
    path("inbox/", views.my_inbox, name="my-inbox"),
    path("inbox/<int:pk>/read/", views.mark_inbox_read, name="inbox-read"),
    path("faqs/", views.faq_list, name="faq-list"),
    path("faqs/<int:pk>/", views.faq_delete, name="faq-delete"),
    path("chatbot/", views.faq_chatbot, name="faq-chatbot"),

    # ── Income/Expense Tracking & Financial Reporting (Epic SCRUM-21, WIP) ──
    path('finance/transactions/', views.finance_list),
    path('finance/add/', views.finance_add),
    path('finance/transactions/<int:pk>/', views.finance_delete),
    path('finance/transactions/<int:pk>/update/', views.finance_update),
    path('finance/stats/', views.finance_stats),
    path('finance/budgets/', views.finance_budgets),
    path('finance/export/', views.finance_export),
]
