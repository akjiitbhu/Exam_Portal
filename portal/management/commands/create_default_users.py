from django.contrib.auth.models import User, Group
from django.core.management.base import BaseCommand

DEFAULT_ACCOUNTS = [
    ("coordinator", "Coordinator"),
    ("staff", "Staff"),
]


class Command(BaseCommand):
    help = "Creates the Coordinator/Staff groups and one default login for each role."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="changeme123",
            help="Password to set on any account this command creates (default: changeme123).",
        )

    def handle(self, *args, **options):
        password = options["password"]
        for group_name in ("Coordinator", "Staff"):
            Group.objects.get_or_create(name=group_name)

        for username, group_name in DEFAULT_ACCOUNTS:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created user '{username}' with password '{password}'"))
            else:
                self.stdout.write(f"User '{username}' already exists, leaving as-is")

            group = Group.objects.get(name=group_name)
            user.groups.add(group)
