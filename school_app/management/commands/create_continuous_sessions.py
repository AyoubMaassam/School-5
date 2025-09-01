from django.core.management.base import BaseCommand, CommandError
from school_app.models import Group, Session
from django.utils import timezone
import datetime

class Command(BaseCommand):
    help = 'Creates sessions for upcoming weeks for continuous groups.'

    def handle(self, *args, **options):
        today = timezone.now().date()
        # Define how far in advance to create sessions (e.g., 4 weeks)
        creation_horizon = today + datetime.timedelta(weeks=4)

        continuous_groups = Group.objects.filter(is_continuous=True)
        self.stdout.write(f"Found {continuous_groups.count()} continuous groups.")

        for group in continuous_groups:
            last_created_date_for_group = group.created_sessions_until

            # Determine the start date for checking/creating sessions
            # If sessions were created until some date, start from the day after that date.
            # Otherwise, start from today.
            # Ensure we don't try to create sessions for dates already passed if last_created_date_for_group is old.
            current_check_date = today
            if last_created_date_for_group:
                current_check_date = max(today, last_created_date_for_group + datetime.timedelta(days=1))

            self.stdout.write(f'Processing group "{group.name}". Last created session: {last_created_date_for_group}. Starting check from: {current_check_date}. Horizon: {creation_horizon}')

            if current_check_date > creation_horizon:
                self.stdout.write(self.style.NOTICE(f'Sessions for group "{group.name}" are already created up to or beyond the horizon ({creation_horizon}). Skipping.'))
                continue

            new_sessions_created_for_this_group_in_this_run = False
            # This will track the latest date a session was actually created FOR in this run
            latest_actual_session_date_in_run = last_created_date_for_group

            temp_date_iterator = current_check_date
            while temp_date_iterator <= creation_horizon:
                # Check if the day is the group's scheduled session day
                if temp_date_iterator.weekday() == group.session_day:
                    session_exists = Session.objects.filter(group=group, date=temp_date_iterator).exists()
                    if not session_exists:
                        Session.objects.create(
                            group=group,
                            date=temp_date_iterator,
                            start_time=group.session_start_time,
                            duration=group.session_duration,
                            # teacher_attended will default to None (or False based on model)
                            # teacher_compensated will default to False
                        )
                        self.stdout.write(self.style.SUCCESS(f'Created session for group "{group.name}" on {temp_date_iterator}'))

                        if latest_actual_session_date_in_run is None or temp_date_iterator > latest_actual_session_date_in_run:
                            latest_actual_session_date_in_run = temp_date_iterator
                        new_sessions_created_for_this_group_in_this_run = True
                    else:
                        # If a session on this day already exists, we still want to consider this date
                        # as "processed" for the sake of updating created_sessions_until,
                        # so that the command doesn't re-check it unnecessarily next time if it's within the horizon.
                        # However, only update latest_actual_session_date_in_run if a *new* session was created.
                        # For created_sessions_until, we want to advance it to the end of the horizon processed,
                        # or to the last *actually created* session if that's more meaningful.
                        # The goal of created_sessions_until is to know up to where the system *intended* to create.
                        # Let's update it to the latest date for which a session *was* created or *confirmed* to exist.
                        if latest_actual_session_date_in_run is None or temp_date_iterator > latest_actual_session_date_in_run:
                             # This ensures if we skipped creating because it exists, created_sessions_until still moves forward for this processed day.
                             # but only if we didn't create a newer one.
                             # A better approach: update created_sessions_until at the end to `creation_horizon` for this group if we iterated that far,
                             # or to the last `temp_date_iterator` successfully processed for this group's session_day.
                             pass # No new session, no change to latest_actual_session_date_in_run based on this existing one.

                temp_date_iterator += datetime.timedelta(days=1)

            # After checking all dates up to the horizon for this group:
            # Update created_sessions_until to the latest date for which a session was actually generated OR confirmed.
            # A simpler and robust approach: update to the latest date we attempted to create sessions for, within the horizon.
            # This ensures that next time, we start checking from after this point.
            # If new sessions were created, `latest_actual_session_date_in_run` holds the date of the last one.
            # If no new sessions were created (e.g., all existed or no valid days in range),
            # we should still update created_sessions_until to show the system has processed up to `creation_horizon` for this group.

            # If we iterated through dates for this group (i.e., current_check_date <= creation_horizon)
            # then we should update created_sessions_until to reflect that this period has been processed.
            # The most straightforward is to set it to the end of the period we just checked for this group.
            # The last `temp_date_iterator` value (after loop) is `creation_horizon + 1 day`. So previous day is `creation_horizon`.

            # We should update created_sessions_until to the latest date for which sessions *should* have been created
            # if they fell on the correct weekday and were within the horizon.
            # This means, if we processed up to `creation_horizon`, then `group.created_sessions_until`
            # should become `creation_horizon` if any valid session days were encountered up to that point,
            # or more precisely, the date of the last *potential* session day within that horizon.

            # A simpler logic for created_sessions_until:
            # If we created any new session, update to the date of the latest one created.
            # If we did not create any new one, but we did iterate (current_check_date <= creation_horizon),
            # it means all potential sessions up to creation_horizon either existed or there were no valid days.
            # In this case, we could set created_sessions_until to creation_horizon to avoid re-processing the same empty range.

            final_update_date_for_group = group.created_sessions_until # Keep existing if no changes

            if new_sessions_created_for_this_group_in_this_run:
                final_update_date_for_group = latest_actual_session_date_in_run
            elif current_check_date <= creation_horizon :
                # If we went through the loop but created nothing new (all existed or no valid days)
                # Advance created_sessions_until to the end of the checked period for this group.
                # This avoids re-checking an empty valid range.
                # We need to find the last valid session day for this group within the horizon.
                last_possible_session_day_in_horizon = None
                d = creation_horizon
                while d >= current_check_date:
                    if d.weekday() == group.session_day:
                        last_possible_session_day_in_horizon = d
                        break
                    d -= datetime.timedelta(days=1)

                if last_possible_session_day_in_horizon:
                     final_update_date_for_group = max(final_update_date_for_group if final_update_date_for_group else datetime.date.min , last_possible_session_day_in_horizon)
                else: # No valid session day for this group in the checked range up to horizon
                      # Still, we processed this range. Update to horizon to signify this.
                      final_update_date_for_group = max(final_update_date_for_group if final_update_date_for_group else datetime.date.min, creation_horizon)


            if final_update_date_for_group and (group.created_sessions_until is None or final_update_date_for_group > group.created_sessions_until):
                group.created_sessions_until = final_update_date_for_group
                group.save()
                self.stdout.write(self.style.SUCCESS(f'Updated created_sessions_until for group "{group.name}" to {group.created_sessions_until}'))
            elif new_sessions_created_for_this_group_in_this_run : # Should have been caught by above, but defensive.
                 self.stdout.write(self.style.WARNING(f'New sessions created for "{group.name}" but created_sessions_until was not updated ({group.created_sessions_until} vs {final_update_date_for_group}).'))
            else:
                self.stdout.write(self.style.NOTICE(f'No new sessions created and no update to created_sessions_until needed for group "{group.name}" (already {group.created_sessions_until}).'))


        self.stdout.write(self.style.SUCCESS('Finished creating continuous sessions.'))

```
