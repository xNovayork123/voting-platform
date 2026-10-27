"""
Seed the database with starter FAQs for the AI chatbot (SCRUM-28).

Usage:
    python manage.py seed_faqs          # adds FAQs (skips ones that already exist by question)
    python manage.py seed_faqs --fresh  # deletes ALL existing FAQs first, then adds these
"""

from django.core.management.base import BaseCommand
from voting.models import FAQ

FAQS = [
    {
        "question": "How do I vote on a ballot?",
        "answer": "Open the Ballots page from the sidebar, pick the ballot you want, "
                  "choose your option and confirm. Each member can vote once per ballot.",
        "keywords": "vote, voting, ballot, cast, how to vote",
    },
    {
        "question": "Can I change my vote after submitting?",
        "answer": "No. Once your vote is recorded it is final, so please review your "
                  "choice before confirming.",
        "keywords": "change vote, edit vote, undo, revote, already voted",
    },
    {
        "question": "How do I suggest a new ballot?",
        "answer": "Click the '+ Create' / 'Suggest' button. Your suggestion is sent to an "
                  "admin for review, and becomes a live ballot once approved.",
        "keywords": "suggest, suggestion, propose, new ballot, request ballot",
    },
    {
        "question": "Where can I see the ballots I already voted on?",
        "answer": "Go to 'My Votes' in the sidebar. It lists every ballot you've voted on "
                  "and the option you chose.",
        "keywords": "my votes, history, past votes, what did i vote",
    },
    {
        "question": "How do I upload a document?",
        "answer": "Open DocVault from the sidebar and use the upload button. You can tag "
                  "documents and sort them into categories.",
        "keywords": "document, upload, docvault, file, attach",
    },
    {
        "question": "Who can create announcements?",
        "answer": "Only admins can create and send announcements or reminders. Members "
                  "receive them in the Announcements inbox.",
        "keywords": "announcement, reminder, send message, who can announce, notify",
    },
    {
        "question": "How do I reset my password?",
        "answer": "If you signed up with email and password, use the sign-in screen to "
                  "register again is not needed—contact an admin to reset your password. "
                  "If you signed in with Google, manage your password through Google.",
        "keywords": "password, reset, forgot, login problem, can't sign in",
    },
    {
        "question": "What is a reminder?",
        "answer": "A reminder is a short message admins send to members about upcoming "
                  "events or deadlines, such as a ballot closing soon. It appears in your "
                  "Announcements inbox.",
        "keywords": "reminder, deadline, due, notification, alert",
    },
]


class Command(BaseCommand):
    help = "Seed starter FAQs for the chatbot."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete all existing FAQs before seeding.",
        )

    def handle(self, *args, **options):
        if options["fresh"]:
            deleted, _ = FAQ.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing FAQ(s)."))

        created = 0
        for item in FAQS:
            _, was_created = FAQ.objects.get_or_create(
                question=item["question"],
                defaults={"answer": item["answer"], "keywords": item["keywords"]},
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} new FAQ(s)."))
