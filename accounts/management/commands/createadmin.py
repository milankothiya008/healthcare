from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Creates a superuser/admin account'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Admin username', default='admin')
        parser.add_argument('--email', type=str, help='Admin email', default='admin@healthcare.com')
        parser.add_argument('--password', type=str, help='Admin password', default='admin123')
        parser.add_argument('--first-name', type=str, help='First name', default='Admin')
        parser.add_argument('--last-name', type=str, help='Last name', default='User')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        first_name = options['first_name']
        last_name = options['last_name']

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'User "{username}" already exists.'))
            return

        admin_user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role='ADMIN',
            is_approved=True,
            is_staff=True,
            is_superuser=True
        )

        self.stdout.write(self.style.SUCCESS(f'Successfully created admin user "{username}"'))
        self.stdout.write(self.style.SUCCESS(f'Email: {email}'))
        self.stdout.write(self.style.SUCCESS(f'Password: {password}'))
