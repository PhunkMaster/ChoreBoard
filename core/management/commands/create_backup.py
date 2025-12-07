"""Management command to create database backup."""
import os
import shutil
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from core.models import Backup


class Command(BaseCommand):
    help = "Create a database backup and clean up old backups (7-day retention)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--notes',
            type=str,
            default='',
            help='Optional notes for this backup'
        )
        parser.add_argument(
            '--auto',
            action='store_true',
            help='Mark this as an automatic backup'
        )

    def handle(self, *args, **options):
        notes = options['notes']
        is_manual = not options['auto']

        # Get database file path
        db_path = settings.DATABASES['default']['NAME']

        if not os.path.exists(db_path):
            self.stdout.write(self.style.ERROR(f"Database file not found: {db_path}"))
            return

        # Create backups directory if it doesn't exist
        backups_dir = os.path.join(os.path.dirname(db_path), 'backups')
        os.makedirs(backups_dir, exist_ok=True)

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"db_backup_{timestamp}.sqlite3"
        backup_path = os.path.join(backups_dir, backup_filename)

        try:
            # Copy database file
            self.stdout.write(f"Creating backup: {backup_filename}...")
            shutil.copy2(db_path, backup_path)

            # Get file size
            file_size = os.path.getsize(backup_path)

            # Create backup record
            backup = Backup.objects.create(
                filename=backup_filename,
                file_path=backup_path,
                file_size_bytes=file_size,
                notes=notes,
                is_manual=is_manual
            )

            self.stdout.write(self.style.SUCCESS(
                f"✓ Backup created successfully: {backup_filename} ({backup.get_size_display()})"
            ))

            # Clean up old backups (7-day retention)
            retention_date = timezone.now() - timedelta(days=7)
            old_backups = Backup.objects.filter(created_at__lt=retention_date)

            if old_backups.exists():
                self.stdout.write(f"\nCleaning up backups older than 7 days...")
                deleted_count = 0
                for old_backup in old_backups:
                    # Delete physical file
                    if os.path.exists(old_backup.file_path):
                        try:
                            os.remove(old_backup.file_path)
                            self.stdout.write(f"  Deleted: {old_backup.filename}")
                            deleted_count += 1
                        except OSError as e:
                            self.stdout.write(self.style.WARNING(
                                f"  Could not delete {old_backup.filename}: {e}"
                            ))

                    # Delete database record
                    old_backup.delete()

                self.stdout.write(self.style.SUCCESS(f"✓ Cleaned up {deleted_count} old backup(s)"))

            # Show current backup count
            total_backups = Backup.objects.count()
            self.stdout.write(f"\nTotal backups: {total_backups}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Backup failed: {str(e)}"))
            # Clean up partial backup file if it exists
            if os.path.exists(backup_path):
                os.remove(backup_path)
