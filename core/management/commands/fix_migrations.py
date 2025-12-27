# ChoreBoard - A smart household chore management system
# Copyright (C) 2024 PhunkMaster
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Management command to fix migration state after restoring a selective backup.

This command synchronizes Django's migration history with the actual database schema
by faking all migrations that have already been applied to the database.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.apps import apps


class Command(BaseCommand):
    help = 'Fix migration state after restoring a selective backup'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-history',
            action='store_true',
            help='Clear migration history before faking migrations',
        )

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.WARNING("FIX MIGRATION STATE"))
        self.stdout.write("=" * 80)
        self.stdout.write()

        if options['clear_history']:
            self.stdout.write("Clearing migration history...")
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM django_migrations")
            self.stdout.write(self.style.SUCCESS("  [OK] Migration history cleared"))
            self.stdout.write()

        # Get all app configs
        app_labels = [app.label for app in apps.get_app_configs()]

        # Apps in dependency order (to avoid foreign key issues)
        ordered_apps = [
            'contenttypes',
            'auth',
            'admin',
            'sessions',
            'users',
            'board',
            'chores',
            'core',
            'django_apscheduler',
        ]

        # Add any remaining apps not in the ordered list
        for app_label in app_labels:
            if app_label not in ordered_apps and app_label not in ['api']:
                ordered_apps.append(app_label)

        self.stdout.write("Faking migrations for all apps...")
        self.stdout.write()

        for app_label in ordered_apps:
            if app_label in app_labels:
                try:
                    self.stdout.write(f"  Processing {app_label}...", ending='')
                    call_command('migrate', app_label, '--fake', verbosity=0)
                    self.stdout.write(self.style.SUCCESS(" FAKED"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f" ERROR: {str(e)}"))

        self.stdout.write()
        self.stdout.write("Verifying migration state...")
        call_command('migrate', verbosity=1)

        self.stdout.write()
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("Migration state fixed successfully!"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write()
