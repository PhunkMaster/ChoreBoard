"""
Management command to diagnose chore distribution failures.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Q

from chores.models import Chore, ChoreInstance, ChoreEligibility, Completion
from core.models import RotationState, EvaluationLog
from users.models import User
from core.jobs import should_create_instance_today


class Command(BaseCommand):
    help = 'Diagnose why a chore failed to distribute at expected time'

    def add_arguments(self, parser):
        parser.add_argument('chore', type=str, help='Chore name or ID')
        parser.add_argument(
            '--date',
            type=str,
            help='Date to check (YYYY-MM-DD format, default: today)'
        )

    def handle(self, *args, **options):
        # Parse date
        if options['date']:
            try:
                check_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(self.style.ERROR(
                    'Invalid date format. Use YYYY-MM-DD'
                ))
                return
        else:
            check_date = timezone.localdate()

        # Find chore
        chore_identifier = options['chore']
        try:
            # Try as ID first
            chore = Chore.objects.get(id=int(chore_identifier))
        except (ValueError, Chore.DoesNotExist):
            # Try as name
            try:
                chore = Chore.objects.get(name__iexact=chore_identifier)
            except Chore.DoesNotExist:
                # Try partial match
                chores = Chore.objects.filter(name__icontains=chore_identifier)
                if chores.count() == 0:
                    self.stdout.write(self.style.ERROR(
                        f'No chore found matching: {chore_identifier}'
                    ))
                    return
                elif chores.count() > 1:
                    self.stdout.write(self.style.ERROR(
                        f'Multiple chores found matching "{chore_identifier}":'
                    ))
                    for c in chores:
                        self.stdout.write(f'  - {c.name} (ID: {c.id})')
                    self.stdout.write('\nPlease be more specific or use the chore ID.')
                    return
                else:
                    chore = chores.first()

        # Start diagnostic report
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS('DISTRIBUTION DIAGNOSTIC REPORT'))
        self.stdout.write(f'Chore: {chore.name} (ID: {chore.id})')
        self.stdout.write(f'Date: {check_date}')
        self.stdout.write('=' * 80)
        self.stdout.write('')

        # Section 1: Chore Configuration
        self.stdout.write(self.style.SUCCESS('[1] CHORE CONFIGURATION'))

        self._check_symbol(chore.is_active, 'Is Active', chore.is_active)
        self._check_symbol(True, 'Is Pool', chore.is_pool)
        self._check_symbol(True, 'Is Undesirable', chore.is_undesirable)
        self._check_symbol(True, 'Distribution Time', chore.distribution_time.strftime('%H:%M'))
        self._check_symbol(chore.rescheduled_date is None, 'Rescheduled Date',
                          chore.rescheduled_date or 'None')
        self._check_symbol(True, 'Schedule Type', chore.get_schedule_type_display())
        self.stdout.write('')

        if not chore.is_active:
            self.stdout.write(self.style.ERROR(
                '  ISSUE: Chore is not active - will not be scheduled'
            ))
            self.stdout.write('')

        if chore.rescheduled_date and chore.rescheduled_date != check_date:
            self.stdout.write(self.style.ERROR(
                f'  ISSUE: Chore is rescheduled to {chore.rescheduled_date} - will not run on {check_date}'
            ))
            self.stdout.write('')

        # Section 2: Instance Creation Check
        self.stdout.write(self.style.SUCCESS('[2] INSTANCE CREATION CHECK'))

        # Check for instance on target date
        date_start = timezone.make_aware(datetime.combine(check_date, datetime.min.time()))
        date_end = timezone.make_aware(datetime.combine(check_date, datetime.max.time()))

        instance = ChoreInstance.objects.filter(
            chore=chore,
            due_at__range=(date_start, date_end)
        ).first()

        if instance:
            self._check_symbol(True, 'Instance Found', f'ID: {instance.id}')
            self._check_symbol(True, 'Status', instance.status)
            self._check_symbol(True, 'Distribution Time',
                              instance.distribution_at.strftime('%Y-%m-%d %H:%M'))
            if instance.assigned_to:
                self._check_symbol(True, 'Assigned To', instance.assigned_to.username)
            if instance.assignment_reason:
                self._check_symbol(True, 'Assignment Reason', instance.assignment_reason)
            self.stdout.write('')
        else:
            self._check_symbol(False, 'Instance Found', 'No instance for this date')
            self.stdout.write('')

            # Investigate why instance wasn't created
            self.stdout.write('  Investigating why instance was not created...')
            self.stdout.write('')

            # Check midnight evaluation
            midnight = timezone.make_aware(datetime.combine(check_date, datetime.min.time()))
            midnight_end = midnight + timedelta(minutes=15)

            eval_log = EvaluationLog.objects.filter(
                evaluation_time__range=(midnight, midnight_end)
            ).first()

            if eval_log:
                self.stdout.write(f'  Midnight evaluation ran: {eval_log.evaluation_time.strftime("%Y-%m-%d %H:%M:%S")}')
                self.stdout.write(f'  Created {eval_log.instances_created} instances')
                self.stdout.write('')
            else:
                self.stdout.write(self.style.WARNING(
                    f'  WARNING: No midnight evaluation record found for {check_date}'
                ))
                self.stdout.write('  This could mean midnight_evaluation() did not run')
                self.stdout.write('')

            # Check should_create_instance_today conditions
            self.stdout.write('  Checking should_create_instance_today() conditions:')
            self.stdout.write('')

            # Check for open instances from previous days
            open_instances = ChoreInstance.objects.filter(
                chore=chore
            ).filter(
                ~Q(status__in=['completed', 'skipped'])
            ).exclude(
                due_at__range=(date_start, date_end)
            ).order_by('-due_at')

            if open_instances.exists():
                oldest = open_instances.first()
                self._check_symbol(False, 'BLOCKER',
                                 f'Open instance from {oldest.due_at.strftime("%Y-%m-%d")} exists')
                self.stdout.write(f'      Instance ID: {oldest.id}')
                self.stdout.write(f'      Status: {oldest.status}')
                if oldest.assigned_to:
                    self.stdout.write(f'      Assigned To: {oldest.assigned_to.username}')
                self.stdout.write('')
                self.stdout.write(self.style.ERROR(
                    '      Reason: Lines 455-463 in core/jobs.py prevent duplicate creation'
                ))
                self.stdout.write('      when any open instance exists (not completed/skipped)')
                self.stdout.write('')
            else:
                self._check_symbol(True, 'No Open Instances', 'No blocking instances found')
                self.stdout.write('')

            # Check schedule match
            if chore.is_active:
                would_create = should_create_instance_today(chore, check_date)
                if would_create:
                    self._check_symbol(True, 'Schedule Match',
                                     f'Chore matches {check_date} schedule')
                else:
                    self._check_symbol(False, 'Schedule Match',
                                     f'Chore does not match {check_date} schedule')
                self.stdout.write('')

        # Section 3: Eligibility Check
        self.stdout.write(self.style.SUCCESS('[3] ELIGIBILITY CHECK'))

        if chore.is_undesirable:
            eligibility_records = ChoreEligibility.objects.filter(
                chore=chore
            ).select_related('user')

            if eligibility_records.exists():
                self.stdout.write(f'  Found {eligibility_records.count()} ChoreEligibility records:')
                self.stdout.write('')

                eligible_count = 0
                for record in eligibility_records:
                    user = record.user
                    is_eligible = (
                        user.can_be_assigned and
                        user.is_active and
                        not user.exclude_from_auto_assignment
                    )

                    if is_eligible:
                        eligible_count += 1
                        self._check_symbol(True, user.username,
                                         f'ID: {user.id}, can_be_assigned={user.can_be_assigned}, '
                                         f'is_active={user.is_active}, '
                                         f'exclude_from_auto={user.exclude_from_auto_assignment}')
                    else:
                        reasons = []
                        if not user.can_be_assigned:
                            reasons.append('can_be_assigned=False')
                        if not user.is_active:
                            reasons.append('is_active=False')
                        if user.exclude_from_auto_assignment:
                            reasons.append('exclude_from_auto=True')

                        self._check_symbol(False, user.username,
                                         f'ID: {user.id}, EXCLUDED: {", ".join(reasons)}')
                self.stdout.write('')
                self.stdout.write(f'  Eligible users after filters: {eligible_count}')
                self.stdout.write('')

                if eligible_count == 0:
                    self.stdout.write(self.style.ERROR(
                        '  ISSUE: No eligible users after filtering'
                    ))
                    self.stdout.write('  Result: Instance would remain in POOL with reason="no_eligible_users"')
                    self.stdout.write('')
            else:
                self._check_symbol(False, 'ChoreEligibility Records', 'None found')
                self.stdout.write('')
                self.stdout.write(self.style.ERROR(
                    '  ISSUE: Undesirable chore has no ChoreEligibility records'
                ))
                self.stdout.write('  Result: No users can be assigned')
                self.stdout.write('')
        else:
            self.stdout.write('  Chore is not undesirable - all users eligible')
            self.stdout.write('')

            all_users = User.objects.filter(
                can_be_assigned=True,
                is_active=True,
                exclude_from_auto_assignment=False
            )

            self.stdout.write(f'  Total eligible users: {all_users.count()}')
            for user in all_users[:5]:  # Show first 5
                self.stdout.write(f'    - {user.username} (ID: {user.id})')
            if all_users.count() > 5:
                self.stdout.write(f'    ... and {all_users.count() - 5} more')
            self.stdout.write('')

        # Section 4: Rotation State Check (for undesirable chores)
        if chore.is_undesirable and ChoreEligibility.objects.filter(chore=chore).exists():
            self.stdout.write(self.style.SUCCESS('[4] ROTATION STATE CHECK'))

            yesterday = check_date - timedelta(days=1)
            self.stdout.write(f'  Checking yesterday ({yesterday}) completions:')
            self.stdout.write('')

            rotation_states = RotationState.objects.filter(
                chore=chore
            ).select_related('user')

            if rotation_states.exists():
                available_count = 0
                blocked_count = 0

                for state in rotation_states:
                    user = state.user
                    # Check if user is eligible first
                    if not (user.can_be_assigned and user.is_active and not user.exclude_from_auto_assignment):
                        continue

                    if state.last_completed_date == yesterday:
                        self._check_symbol(False, user.username,
                                         f'Last completed: {state.last_completed_date} (BLOCKED)')
                        blocked_count += 1
                    else:
                        last_date = state.last_completed_date or 'never'
                        self._check_symbol(True, user.username,
                                         f'Last completed: {last_date} (OK)')
                        available_count += 1

                self.stdout.write('')
                self.stdout.write(f'  Available users after rotation filter: {available_count}')
                self.stdout.write(f'  Blocked users (completed yesterday): {blocked_count}')
                self.stdout.write('')

                if available_count == 0 and blocked_count > 0:
                    self.stdout.write(self.style.ERROR(
                        '  ISSUE: All eligible users completed this chore yesterday'
                    ))
                    self.stdout.write('  Result: Instance would remain in POOL with reason="all_completed_yesterday"')
                    self.stdout.write('  This is the "purple state" - will resolve tomorrow')
                    self.stdout.write('')
            else:
                self.stdout.write('  No RotationState records found')
                self.stdout.write('  This means the chore has never been completed')
                self.stdout.write('')

        # Section 5: Difficult Chore Check (if applicable)
        if chore.is_difficult and instance and instance.status == ChoreInstance.POOL:
            self.stdout.write(self.style.SUCCESS('[5] DIFFICULT CHORE CHECK'))

            # Check which users have difficult chores today
            today = timezone.localdate()
            today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
            today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))

            if chore.is_undesirable:
                # Use ChoreEligibility users
                eligible_user_list = ChoreEligibility.objects.filter(
                    chore=chore
                ).select_related('user').values_list('user', flat=True)
                check_users = User.objects.filter(
                    id__in=eligible_user_list,
                    can_be_assigned=True,
                    is_active=True,
                    exclude_from_auto_assignment=False
                )
            else:
                # Use all eligible users
                check_users = User.objects.filter(
                    can_be_assigned=True,
                    is_active=True,
                    exclude_from_auto_assignment=False
                )

            users_with_difficult = []
            users_without_difficult = []

            for user in check_users:
                has_difficult = ChoreInstance.objects.filter(
                    assigned_to=user,
                    status__in=[ChoreInstance.ASSIGNED, ChoreInstance.COMPLETED],
                    chore__is_difficult=True,
                    due_at__range=(today_start, today_end)
                ).exclude(id=instance.id).exists()

                if has_difficult:
                    # Find which difficult chore they have
                    difficult_instance = ChoreInstance.objects.filter(
                        assigned_to=user,
                        status__in=[ChoreInstance.ASSIGNED, ChoreInstance.COMPLETED],
                        chore__is_difficult=True,
                        due_at__range=(today_start, today_end)
                    ).exclude(id=instance.id).first()
                    users_with_difficult.append((user, difficult_instance))
                else:
                    users_without_difficult.append(user)

            self.stdout.write(f'  Users with difficult chore today: {len(users_with_difficult)}')
            for user, difficult_instance in users_with_difficult:
                self._check_symbol(False, user.username,
                                 f'{difficult_instance.chore.name} ({difficult_instance.status})')

            self.stdout.write('')
            self.stdout.write(f'  Users without difficult chore: {len(users_without_difficult)}')
            for user in users_without_difficult:
                self._check_symbol(True, user.username, 'Available for difficult chore')

            self.stdout.write('')

            if len(users_without_difficult) == 0:
                self.stdout.write(self.style.ERROR(
                    '  ISSUE: All users have reached difficult chore limit'
                ))
                self.stdout.write('  This is likely why the chore was not assigned')
                self.stdout.write('')

        # Section 6: Root Cause Summary
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS('ROOT CAUSE ANALYSIS'))
        self.stdout.write('=' * 80)
        self.stdout.write('')

        if not instance:
            # No instance created
            if not chore.is_active:
                self.stdout.write(self.style.ERROR('[X] Instance was NOT CREATED'))
                self.stdout.write('  Reason: Chore is not active')
                self.stdout.write('  Fix: Set chore.is_active=True in admin')
            elif chore.rescheduled_date and chore.rescheduled_date != check_date:
                self.stdout.write(self.style.ERROR('[X] Instance was NOT CREATED'))
                self.stdout.write(f'  Reason: Chore is rescheduled to {chore.rescheduled_date}')
                self.stdout.write('  Fix: Clear rescheduled_date or wait until that date')
            elif open_instances.exists():
                oldest = open_instances.first()
                self.stdout.write(self.style.ERROR('[X] Instance was NOT CREATED'))
                self.stdout.write(f'  Reason: Open instance from {oldest.due_at.strftime("%Y-%m-%d")} exists (ID: {oldest.id})')
                self.stdout.write('  Fix: Complete or skip the orphaned instance:')
                self.stdout.write(f'    python manage.py shell -c "from chores.models import ChoreInstance; '
                                f'ChoreInstance.objects.get(id={oldest.id}).status=\'skipped\'; '
                                f'ChoreInstance.objects.get(id={oldest.id}).save()"')
            else:
                self.stdout.write(self.style.ERROR('[X] Instance was NOT CREATED'))
                self.stdout.write('  Reason: Unknown - check midnight_evaluation logs')
                self.stdout.write('  Possible: Schedule does not match this date')
        else:
            # Instance exists but not assigned
            if instance.status == ChoreInstance.POOL:
                if instance.distribution_at > timezone.now():
                    self.stdout.write(self.style.WARNING('[!] Instance in POOL (not yet distributed)'))
                    self.stdout.write(f'  Distribution time: {instance.distribution_at.strftime("%Y-%m-%d %H:%M")}')
                    self.stdout.write(f'  Current time: {timezone.now().strftime("%Y-%m-%d %H:%M")}')
                    self.stdout.write('  Status: Waiting for distribution time')
                elif instance.assignment_reason == ChoreInstance.REASON_NO_ELIGIBLE:
                    self.stdout.write(self.style.ERROR('[X] Instance NOT ASSIGNED'))
                    self.stdout.write('  Reason: No eligible users')
                    if chore.is_undesirable:
                        self.stdout.write('  Fix: Add ChoreEligibility records or update user flags')
                    else:
                        self.stdout.write('  Fix: Update user flags (can_be_assigned, is_active, exclude_from_auto_assignment)')
                elif instance.assignment_reason == ChoreInstance.REASON_ALL_COMPLETED_YESTERDAY:
                    self.stdout.write(self.style.ERROR('[X] Instance NOT ASSIGNED (Purple State)'))
                    self.stdout.write('  Reason: All eligible users completed this chore yesterday')
                    self.stdout.write('  Fix: Wait until tomorrow - rotation will allow assignment')
                elif instance.assignment_reason == ChoreInstance.REASON_DIFFICULT_CHORE_LIMIT:
                    self.stdout.write(self.style.ERROR('[X] Instance NOT ASSIGNED'))
                    self.stdout.write('  Reason: All eligible users have reached difficult chore limit (1 per day)')
                    self.stdout.write('  Fix: Wait for tomorrow or complete/skip existing difficult chores')
                else:
                    self.stdout.write(self.style.ERROR('[X] Instance NOT ASSIGNED'))
                    self.stdout.write(f'  Reason: {instance.assignment_reason or "Unknown"}')
                    self.stdout.write('  Check distribution_check logs for details')
            elif instance.status == ChoreInstance.ASSIGNED:
                self.stdout.write(self.style.SUCCESS('[OK] Instance ASSIGNED successfully'))
                self.stdout.write(f'  Assigned to: {instance.assigned_to.username}')
                self.stdout.write(f'  Assignment reason: {instance.assignment_reason or "auto"}')
            elif instance.status == ChoreInstance.COMPLETED:
                self.stdout.write(self.style.SUCCESS('[OK] Instance COMPLETED'))
                self.stdout.write(f'  Assigned to: {instance.assigned_to.username}')
            elif instance.status == ChoreInstance.SKIPPED:
                self.stdout.write(self.style.WARNING('[!] Instance SKIPPED'))

        self.stdout.write('')
        self.stdout.write('=' * 80)

    def _check_symbol(self, is_ok, label, value):
        """Print a labeled value with a check mark or X."""
        # Use ASCII characters for Windows compatibility
        symbol = self.style.SUCCESS('[OK]') if is_ok else self.style.ERROR('[X]')
        self.stdout.write(f'  {symbol} {label}: {value}')
