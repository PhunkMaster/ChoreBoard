"""
ChoreBoard setup wizard management command.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import User
from core.models import Settings, Streak


class Command(BaseCommand):
    help = 'Initial setup wizard for ChoreBoard'

    def add_arguments(self, parser):
        parser.add_argument(
            '--non-interactive',
            action='store_true',
            help='Run in non-interactive mode (skip prompts)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('ChoreBoard Setup Wizard'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')

        # Check if setup already done
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.WARNING('Setup already completed!'))
            self.stdout.write(self.style.WARNING('An admin user already exists.'))
            self.stdout.write('')

            if not options['non_interactive']:
                response = input('Do you want to create another admin user? (y/N): ')
                if response.lower() != 'y':
                    self.stdout.write(self.style.SUCCESS('Setup wizard cancelled.'))
                    return

        # Step 1: Create admin user
        self.stdout.write(self.style.SUCCESS('Step 1: Create Admin User'))
        self.stdout.write('=' * 60)

        if options['non_interactive']:
            self.stdout.write(self.style.ERROR('Cannot create user in non-interactive mode.'))
            self.stdout.write(self.style.ERROR('Please run without --non-interactive flag.'))
            return

        try:
            with transaction.atomic():
                # Get username
                while True:
                    username = input('Enter admin username [admin]: ').strip() or 'admin'
                    if User.objects.filter(username=username).exists():
                        self.stdout.write(self.style.ERROR(f'Username "{username}" already exists. Try another.'))
                    else:
                        break

                # Get email
                email = input('Enter admin email (optional): ').strip()

                # Get password
                from django.contrib.auth.password_validation import validate_password
                from django.core.exceptions import ValidationError

                while True:
                    password = input('Enter admin password: ')
                    password_confirm = input('Confirm password: ')

                    if password != password_confirm:
                        self.stdout.write(self.style.ERROR('Passwords do not match. Try again.'))
                        continue

                    # Validate password
                    try:
                        validate_password(password)
                        break
                    except ValidationError as e:
                        self.stdout.write(self.style.ERROR('Password validation failed:'))
                        for error in e.messages:
                            self.stdout.write(self.style.ERROR(f'  - {error}'))

                # Create admin user
                admin = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                    can_be_assigned=True,
                    eligible_for_points=True
                )

                # Create streak for admin
                Streak.objects.create(user=admin)

                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS(f'✓ Admin user "{username}" created successfully!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating admin user: {str(e)}'))
            return

        # Step 2: Initialize settings
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Step 2: Initialize Settings'))
        self.stdout.write('=' * 60)

        try:
            settings = Settings.get_settings()
            settings.updated_by = admin
            settings.save()

            self.stdout.write(self.style.SUCCESS('✓ Settings initialized:'))
            self.stdout.write(f'  - Points to dollar rate: {settings.points_to_dollar_rate}')
            self.stdout.write(f'  - Max claims per day: {settings.max_claims_per_day}')
            self.stdout.write(f'  - Undo time limit: {settings.undo_time_limit_hours} hours')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error initializing settings: {str(e)}'))

        # Step 3: Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Setup Complete!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write('Next steps:')
        self.stdout.write('1. Start the development server: python manage.py runserver')
        self.stdout.write('2. Visit the admin interface: http://127.0.0.1:8000/admin')
        self.stdout.write(f'3. Log in with username: {username}')
        self.stdout.write('')
        self.stdout.write('Configure your chores and users in the admin interface.')
        self.stdout.write('')
