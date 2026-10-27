"""
Seed the database with example ballots.

Usage:
    python manage.py seed_ballots          # adds examples (skips ones that already exist by title)
    python manage.py seed_ballots --fresh  # deletes ALL existing ballots first, then adds examples

End dates are intentionally mixed so you can see every UI state:
- far-future ballots  -> "Open"
- ending within 24h   -> yellow "Ending soon" badge + countdown
- end date in the past -> auto "Closed" (voting disabled)
- status="closed"      -> "Closed"
"""

import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from voting.models import Ballot

DAY = datetime.timedelta(days=1)
HOUR = datetime.timedelta(hours=1)

# (title, description, options, end_offset_from_now, status, category)
EXAMPLES = [
    ("🎬 Best Movie Genre", "Which movie genre do you enjoy the most?",
        ["Action", "Comedy", "Drama", "Horror", "Sci-Fi"], 14 * DAY, "open", "movies"),
    ("🍕 Favorite Food", "Pick your all-time favorite dish.",
        ["Pizza", "Burger", "Sushi", "Tacos", "Pasta"], 10 * DAY, "open", "food"),
    ("⚽ Top Sport", "Which sport do you love to watch?",
        ["Football", "Basketball", "Tennis", "Formula 1"], 7 * DAY, "open", "sports"),
    ("📱 Best Phone Brand", "Which phone brand would you choose?",
        ["iPhone", "Samsung", "Xiaomi", "Google Pixel"], 5 * DAY, "open", "technology"),
    ("💻 Best Programming Language", "What's your go-to language?",
        ["Python", "JavaScript", "Java", "C#", "Go"], 3 * DAY, "open", "technology"),
    ("📚 Reading Format", "How do you prefer to read?",
        ["Paperback", "E-book", "Audiobook"], 12 * DAY, "open", "general"),
    ("🚗 Car of the Future", "Which powertrain is the future?",
        ["Electric", "Hybrid", "Hydrogen", "Gasoline"], 9 * DAY, "open", "general"),
    ("🏖️ Dream Vacation", "Where would you like to travel next?",
        ["Beach", "Mountains", "City break", "Countryside"], 18 * HOUR, "open", "travel"),   # ending soon
    ("☕ Morning Drink", "What gets you started in the morning?",
        ["Coffee", "Tea", "Fresh juice", "Water"], 6 * HOUR, "open", "food"),               # ending soon
    ("🐶 Best Pet", "Which pet makes the best companion?",
        ["Dog", "Cat", "Bird", "Fish"], 2 * HOUR, "open", "general"),                          # ending very soon
    ("🎮 Best Gaming Console", "Which console wins this generation?",
        ["PS5", "Xbox Series X", "Nintendo Switch", "PC"], -2 * DAY, "open", "gaming"),        # ended by date
    ("🌳 Favorite Season", "Which season is the best?",
        ["Spring", "Summer", "Autumn", "Winter"], -5 * DAY, "closed", "general"),              # closed
]


class Command(BaseCommand):
    help = "Seed the database with example ballots (varied open/ending-soon/closed states)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete all existing ballots before seeding.",
        )

    def handle(self, *args, **options):
        now = timezone.now()

        if options["fresh"]:
            deleted, _ = Ballot.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing object(s)."))

        created = 0
        skipped = 0
        for title, description, options_list, end_offset, status, category in EXAMPLES:
            if Ballot.objects.filter(title=title).exists():
                skipped += 1
                continue
            Ballot.objects.create(
                title=title,
                description=description,
                options=options_list,
                category=category,
                start_date=now - 7 * DAY,
                end_date=now + end_offset,
                status=status,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created {created} ballot(s), skipped {skipped} (already existed)."
        ))
