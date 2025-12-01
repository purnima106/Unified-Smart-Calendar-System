from datetime import datetime, timedelta
from models.event_model import Event, db
from models.user_model import User
import json
import pytz

class ConflictDetectionService:
    """Service for detecting calendar conflicts and suggesting free time slots"""
    
    def __init__(self):
        self.working_hours = {
            'start': 0,  # 9 A
            'end': 24    # 5 PM
        }
        self.min_slot_duration = 30  # minutes
        self.ist_tz = pytz.timezone('Asia/Kolkata')
    
    def detect_conflicts(self, user_id, start_date=None, end_date=None):
        """Detect conflicts for a user's events within a date range
        
        This method now checks events from all CalendarConnections associated with the user,
        even if events were created under different user_ids (for backward compatibility).
        """
        try:
            from models.calendar_connection_model import CalendarConnection
            
            if not start_date:
                # Use IST for consistent timezone handling
                start_date = datetime.now(self.ist_tz).date()
            if not end_date:
                end_date = start_date + timedelta(days=30)
            
            print(f"Detecting conflicts for user {user_id} from {start_date} to {end_date}")
            
            # Get current time in IST for filtering past events
            current_time_ist = datetime.now(self.ist_tz)
            current_time_naive = current_time_ist.replace(tzinfo=None)
            print(f"Current time (IST): {current_time_ist.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            # Convert date range to datetime range in IST
            start_datetime = datetime.combine(start_date, datetime.min.time())
            start_datetime = self.ist_tz.localize(start_datetime)
            end_datetime = datetime.combine(end_date, datetime.max.time())
            end_datetime = self.ist_tz.localize(end_datetime)
            
            # Get all CalendarConnections for this user to find all connected account emails
            connections = CalendarConnection.query.filter_by(
                user_id=user_id,
                is_active=True,
                is_connected=True
            ).all()
            
            connected_emails = [conn.provider_account_email for conn in connections]
            connected_user_ids = [conn.user_id for conn in connections]
            connected_user_ids.append(user_id)  # Also include the main user_id
            connected_user_ids = list(set(connected_user_ids))  # Remove duplicates
            
            print(f"Found {len(connections)} active connections for user {user_id}")
            if connections:
                for conn in connections:
                    print(f"  - {conn.provider}: {conn.provider_account_email} (user_id: {conn.user_id})")
            print(f"Connected account emails: {connected_emails}")
            print(f"Checking events for user_ids: {connected_user_ids}")
            
            # Get all events for the user in the date range
            # Check by user_id OR by organizer email (to catch events from all connected accounts)
            # This handles cases where events might be under different user_ids
            if connected_emails:
                # Build OR conditions for matching events
                or_conditions = []
                
                # Match by user_id
                or_conditions.append(Event.user_id.in_(connected_user_ids))
                
                # Match by organizer email
                or_conditions.append(Event.organizer.in_(connected_emails))
                
                # Match by provider_event_id format: "email:event_id"
                for email in connected_emails:
                    or_conditions.append(Event.provider_event_id.like(f"{email}:%"))
                
                # Combine all OR conditions
                # Only include future/current events (end_time >= current_time)
                events = Event.query.filter(
                    db.or_(*or_conditions),
                    Event.start_time < end_datetime.replace(tzinfo=None),  # Event starts before range ends
                    Event.end_time > start_datetime.replace(tzinfo=None),   # Event ends after range starts
                    Event.end_time >= current_time_naive  # Only future/current events (not past)
                ).order_by(Event.start_time).all()

                # Remove mirror blockers (bidirectional sync placeholders)
                events = [
                    event for event in events
                    if not ((event.title or '').lower().startswith('[mirror]'))
                ]
                
                # Deduplicate events: Remove duplicates based on title, start_time, and organizer
                # This prevents showing the same event multiple times (e.g., original + synced version)
                seen_events = {}
                deduplicated_events = []
                for event in events:
                    # Create a unique key based on title (without [SYNCED] prefix), start_time, and organizer
                    title_key = event.title.replace('[SYNCED] ', '').strip()  # Remove [SYNCED] prefix for comparison
                    event_key = (title_key, event.start_time, event.organizer)
                    
                    # Only add if we haven't seen this exact event before
                    if event_key not in seen_events:
                        seen_events[event_key] = event
                        deduplicated_events.append(event)
                    else:
                        # If duplicate found, prefer the one without [SYNCED] prefix (original)
                        existing_event = seen_events[event_key]
                        if '[SYNCED]' in event.title and '[SYNCED]' not in existing_event.title:
                            # Current event is synced, existing is original - keep existing
                            continue
                        elif '[SYNCED]' not in event.title and '[SYNCED]' in existing_event.title:
                            # Current event is original, existing is synced - replace
                            deduplicated_events.remove(existing_event)
                            seen_events[event_key] = event
                            deduplicated_events.append(event)
                        # If both are synced or both are original, keep the first one
                
                events = deduplicated_events
                print(f"After deduplication: {len(events)} unique events")
            else:
                # Fallback: just check by user_id
                # Only include future/current events (end_time >= current_time)
                events = Event.query.filter(
                    Event.user_id == user_id,
                    Event.start_time < end_datetime.replace(tzinfo=None),
                    Event.end_time > start_datetime.replace(tzinfo=None),
                    Event.end_time >= current_time_naive  # Only future/current events (not past)
                ).order_by(Event.start_time).all()

                events = [
                    event for event in events
                    if not ((event.title or '').lower().startswith('[mirror]'))
                ]
                
                # Deduplicate events for fallback case too
                seen_events = {}
                deduplicated_events = []
                for event in events:
                    title_key = event.title.replace('[SYNCED] ', '').strip()
                    event_key = (title_key, event.start_time, event.organizer)
                    
                    if event_key not in seen_events:
                        seen_events[event_key] = event
                        deduplicated_events.append(event)
                    else:
                        existing_event = seen_events[event_key]
                        if '[SYNCED]' in event.title and '[SYNCED]' not in existing_event.title:
                            continue
                        elif '[SYNCED]' not in event.title and '[SYNCED]' in existing_event.title:
                            deduplicated_events.remove(existing_event)
                            seen_events[event_key] = event
                            deduplicated_events.append(event)
                
                events = deduplicated_events
                print(f"After deduplication (fallback): {len(events)} unique events")
            
            print(f"Found {len(events)} events to check for conflicts (future/current events only)")
            if len(events) > 0:
                print(f"  Date range: {start_datetime.replace(tzinfo=None)} to {end_datetime.replace(tzinfo=None)}")
                print(f"  Current time filter: Only events ending at or after {current_time_naive}")
                print(f"  Event samples:")
                for event in events[:5]:  # Show first 5 events
                    is_future = event.end_time >= current_time_naive
                    status = "FUTURE" if event.start_time > current_time_naive else "CURRENT" if event.start_time <= current_time_naive <= event.end_time else "PAST"
                    print(f"    - {event.title} at {event.start_time} - {event.end_time} ({status}) (User: {event.user_id}, Provider: {event.provider}, Organizer: {event.organizer or 'N/A'})")
                if len(events) > 5:
                    print(f"    ... and {len(events) - 5} more events")
                
                # Group events by user_id for debugging
                events_by_user = {}
                for event in events:
                    if event.user_id not in events_by_user:
                        events_by_user[event.user_id] = []
                    events_by_user[event.user_id].append(event)
                print(f"  Events grouped by user_id: {[(uid, len(evts)) for uid, evts in events_by_user.items()]}")
            else:
                print(f"  WARNING: No events found for user {user_id} in date range!")
                # Check if user has any events at all
                all_user_events = Event.query.filter_by(user_id=user_id).count()
                print(f"  Total events for user {user_id}: {all_user_events}")
                
                # If no events found with connections, try finding events by organizer email directly
                if connected_emails:
                    print(f"  Trying to find events by organizer email directly...")
                    direct_events = Event.query.filter(
                        Event.organizer.in_(connected_emails),
                        Event.start_time < end_datetime.replace(tzinfo=None),
                        Event.end_time > start_datetime.replace(tzinfo=None),
                        Event.end_time >= current_time_naive  # Only future/current events (not past)
                    ).all()
                    print(f"  Found {len(direct_events)} events by organizer email (future/current only)")
                    if direct_events:
                        events = direct_events
                        print(f"  Using {len(events)} events found by organizer email")
            
            conflicts = []
            
            # Check for overlapping events
            # Note: All events in the list are already filtered to be future/current only
            print(f"\nChecking {len(events)} events for overlaps (all are future/current events)...")
            overlap_count = 0
            for i, event1 in enumerate(events):
                # Double-check: skip if event has already ended
                if event1.end_time < current_time_naive:
                    print(f"  Skipping past event: '{event1.title}' (ended at {event1.end_time})")
                    continue
                
                event1_conflicts = []
                
                for j, event2 in enumerate(events):
                    if i != j:
                        # Double-check: skip if conflicting event has already ended
                        if event2.end_time < current_time_naive:
                            continue
                        
                        if self._events_overlap(event1, event2):
                            event1_conflicts.append(event2.id)
                            overlap_count += 1
                            print(f"  ✓ Conflict #{overlap_count}: '{event1.title}' overlaps with '{event2.title}'")
                
                if event1_conflicts:
                    # Update event with conflict information
                    try:
                        event1.set_conflict_with(event1_conflicts)
                        # Get full details of conflicting events (only future/current)
                        conflicting_events_details = [e.to_dict() for e in events if e.id in event1_conflicts and e.end_time >= current_time_naive]
                        conflicting_events_list = [e for e in events if e.id in event1_conflicts and e.end_time >= current_time_naive]
                        conflicts.append({
                            'event': event1.to_dict(),
                            'conflicting_events': [e.id for e in events if e.id in event1_conflicts],
                            'conflicting_events_details': conflicting_events_details,  # Add full event details
                            'conflict_type': self._get_conflict_type(event1, conflicting_events_list)
                        })
                        print(f"  Added conflict record for '{event1.title}' with {len(event1_conflicts)} conflicting event(s)")
                    except Exception as e:
                        print(f"  ERROR setting conflict for event {event1.id}: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        continue
            
            # Commit conflict updates to database
            try:
                db.session.commit()
                print(f"Detected {len(conflicts)} conflicts")
            except Exception as e:
                print(f"Error committing conflict updates: {str(e)}")
                db.session.rollback()
            
            return conflicts
            
        except Exception as e:
            print(f"Error in detect_conflicts: {str(e)}")
            return []
    
    def _events_overlap(self, event1, event2):
        """Check if two events overlap in time with improved logic"""
        try:
            # Handle all-day events
            if event1.all_day or event2.all_day:
                # All-day events conflict if they're on the same day
                return event1.start_time.date() == event2.start_time.date()
            
            # Regular events overlap if one starts before the other ends
            # Use a more lenient check - events conflict if they share any time
            event1_start = event1.start_time
            event1_end = event1.end_time
            event2_start = event2.start_time
            event2_end = event2.end_time
            
            # Normalize to naive datetime for comparison (remove timezone if present)
            if hasattr(event1_start, 'tzinfo') and event1_start.tzinfo is not None:
                event1_start = event1_start.replace(tzinfo=None)
            if hasattr(event1_end, 'tzinfo') and event1_end.tzinfo is not None:
                event1_end = event1_end.replace(tzinfo=None)
            if hasattr(event2_start, 'tzinfo') and event2_start.tzinfo is not None:
                event2_start = event2_start.replace(tzinfo=None)
            if hasattr(event2_end, 'tzinfo') and event2_end.tzinfo is not None:
                event2_end = event2_end.replace(tzinfo=None)
            
            # Events overlap if: event1 starts before event2 ends AND event2 starts before event1 ends
            # This catches: same start time, overlapping times, one contained in the other
            overlap = (event1_start < event2_end) and (event2_start < event1_end)
            
            # Debug logging for same-time events
            time_diff = abs((event1_start - event2_start).total_seconds())
            if time_diff < 300:  # Within 5 minutes
                print(f"  Checking events at similar time (diff: {time_diff}s):")
                print(f"    Event1: '{event1.title}' {event1_start} - {event1_end}")
                print(f"    Event2: '{event2.title}' {event2_start} - {event2_end}")
                print(f"    Overlap check: ({event1_start} < {event2_end}) = {event1_start < event2_end}")
                print(f"    Overlap check: ({event2_start} < {event1_end}) = {event2_start < event1_end}")
                print(f"    Result: {'OVERLAP' if overlap else 'NO OVERLAP'}")
            
            if overlap:
                print(f"  ✓ Overlap detected: '{event1.title}' ({event1.provider}) overlaps with '{event2.title}' ({event2.provider})")
                print(f"    Event1: {event1_start} - {event1_end} (Organizer: {event1.organizer or 'N/A'})")
                print(f"    Event2: {event2_start} - {event2_end} (Organizer: {event2.organizer or 'N/A'})")
            
            return overlap
            
        except Exception as e:
            print(f"Error checking overlap between events {event1.id} and {event2.id}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _get_conflict_type(self, event, conflicting_events):
        """Determine the type of conflict"""
        try:
            if len(conflicting_events) == 1:
                other_event = conflicting_events[0]
                if event.provider != other_event.provider:
                    return 'cross_provider'
                else:
                    return 'same_provider'
            else:
                return 'multiple_conflicts'
        except Exception as e:
            print(f"Error determining conflict type: {str(e)}")
            return 'unknown'
    
    def find_free_slots(self, user_id, date, duration_minutes=60, 
                       start_hour=None, end_hour=None):
        """Find free time slots for scheduling on a specific date
        
        This method now checks events from all CalendarConnections associated with the user,
        even if events were created under different user_ids (for backward compatibility).
        Only future/current free slots are returned.
        """
        try:
            from models.calendar_connection_model import CalendarConnection
            
            if not start_hour:
                start_hour = self.working_hours['start']
            if not end_hour:
                end_hour = self.working_hours['end']
            
            # Get current time in IST for filtering past events
            current_time_ist = datetime.now(self.ist_tz)
            current_time_naive = current_time_ist.replace(tzinfo=None)
            
            print(f"Finding free slots for user {user_id} on {date} for {duration_minutes} minutes")
            print(f"Time range: {start_hour}:00 to {end_hour}:00")
            print(f"Current time (IST): {current_time_ist.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            # Get all CalendarConnections for this user to find all connected account emails
            connections = CalendarConnection.query.filter_by(
                user_id=user_id,
                is_active=True,
                is_connected=True
            ).all()
            
            connected_emails = [conn.provider_account_email for conn in connections]
            connected_user_ids = [conn.user_id for conn in connections]
            connected_user_ids.append(user_id)  # Also include the main user_id
            connected_user_ids = list(set(connected_user_ids))  # Remove duplicates
            
            print(f"Found {len(connections)} active connections for user {user_id}")
            if connections:
                for conn in connections:
                    print(f"  - {conn.provider}: {conn.provider_account_email}")
            
            # Get all events for the specified date from all connected accounts
            start_of_day = datetime.combine(date, datetime.min.time())
            end_of_day = start_of_day + timedelta(days=1)
            
            # Query events by user_id OR by organizer email (to catch events from all connected accounts)
            if connected_emails:
                # Build OR conditions for matching events
                or_conditions = []
                
                # Match by user_id
                or_conditions.append(Event.user_id.in_(connected_user_ids))
                
                # Match by organizer email
                or_conditions.append(Event.organizer.in_(connected_emails))
                
                # Match by provider_event_id format: "email:event_id"
                for email in connected_emails:
                    or_conditions.append(Event.provider_event_id.like(f"{email}:%"))
                
                # Combine all OR conditions and filter by date
                events = Event.query.filter(
                    db.or_(*or_conditions),
                    Event.start_time >= start_of_day,
                    Event.end_time < end_of_day,
                    Event.end_time >= current_time_naive  # Only future/current events
                ).order_by(Event.start_time).all()
            else:
                # Fallback: just check by user_id
                events = Event.query.filter(
                    Event.user_id == user_id,
                    Event.start_time >= start_of_day,
                    Event.end_time < end_of_day,
                    Event.end_time >= current_time_naive  # Only future/current events
                ).order_by(Event.start_time).all()
            
            print(f"Found {len(events)} events on {date} (future/current only)")
            
            # Create busy time ranges
            busy_ranges = []
            for event in events:
                if event.all_day:
                    # All-day events block the entire day
                    busy_ranges.append((start_of_day, end_of_day))
                else:
                    busy_ranges.append((event.start_time, event.end_time))
            
            # Merge overlapping busy ranges
            busy_ranges = self._merge_time_ranges(busy_ranges)
            
            # Find free slots
            free_slots = []
            
            # Start from the beginning of the day or current time (whichever is later)
            slot_start_time = start_of_day.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            
            # If the date is today, start from current time instead of start_hour
            if date == current_time_ist.date():
                # Use current time if it's later than the start hour
                if current_time_naive > slot_start_time:
                    slot_start_time = current_time_naive
                    # Round up to the next 15-minute interval for cleaner slots
                    minutes = slot_start_time.minute
                    rounded_minutes = ((minutes // 15) + 1) * 15
                    if rounded_minutes >= 60:
                        slot_start_time = slot_start_time.replace(hour=slot_start_time.hour + 1, minute=0, second=0, microsecond=0)
                    else:
                        slot_start_time = slot_start_time.replace(minute=rounded_minutes, second=0, microsecond=0)
                print(f"Date is today, starting from current time: {slot_start_time}")
            else:
                print(f"Date is in the future, starting from {start_hour}:00")
            
            end_time = start_of_day.replace(hour=end_hour, minute=0, second=0, microsecond=0)
            
            # Don't show slots if the end time is in the past
            if end_time < current_time_naive:
                print(f"End time {end_time} is in the past, no free slots available")
                return []
            
            current_time = slot_start_time
            
            while current_time < end_time:
                slot_end = current_time + timedelta(minutes=duration_minutes)
                
                # Skip if slot end time is past the end_time limit
                if slot_end > end_time:
                    break
                
                # Skip if slot is in the past
                if current_time < current_time_naive:
                    current_time += timedelta(minutes=self.min_slot_duration)
                    continue
                
                # Check if this slot conflicts with any busy time
                slot_conflicts = False
                for busy_start, busy_end in busy_ranges:
                    if (current_time < busy_end and slot_end > busy_start):
                        slot_conflicts = True
                        # Move current_time to the end of the conflicting event
                        current_time = max(current_time + timedelta(minutes=self.min_slot_duration), busy_end)
                        break
                
                if not slot_conflicts:
                    free_slots.append({
                        'start_time': current_time.isoformat(),
                        'end_time': slot_end.isoformat(),
                        'duration_minutes': duration_minutes
                    })
                    current_time += timedelta(minutes=self.min_slot_duration)
                # If there was a conflict, current_time was already updated
            
            print(f"Found {len(free_slots)} free slots")
            if free_slots:
                print(f"  First slot: {free_slots[0]['start_time']} to {free_slots[0]['end_time']}")
                print(f"  Last slot: {free_slots[-1]['start_time']} to {free_slots[-1]['end_time']}")
            return free_slots
            
        except Exception as e:
            print(f"Error in find_free_slots: {str(e)}")
            return []
    
    def _merge_time_ranges(self, ranges):
        """Merge overlapping time ranges to avoid duplicate processing"""
        if not ranges:
            return []
        
        # Sort ranges by start time
        sorted_ranges = sorted(ranges, key=lambda x: x[0])
        merged = [sorted_ranges[0]]
        
        for current in sorted_ranges[1:]:
            last = merged[-1]
            # If current range overlaps with the last merged range
            if current[0] <= last[1]:
                # Merge them by extending the end time
                merged[-1] = (last[0], max(last[1], current[1]))
            else:
                # No overlap, add current range
                merged.append(current)
        
        return merged
    
    def suggest_meeting_time(self, user_id, duration_minutes=60, 
                           start_date=None, end_date=None, 
                           preferred_days=None, preferred_hours=None):
        """Suggest the best meeting time based on availability"""
        try:
            if not start_date:
                start_date = datetime.utcnow().date()
            if not end_date:
                end_date = start_date + timedelta(days=7)
            
            if not preferred_days:
                preferred_days = [0, 1, 2, 3, 4]  # Monday to Friday
            
            if not preferred_hours:
                preferred_hours = {
                    'start': 9,
                    'end': 17
                }
            
            print(f"Suggesting meeting times for user {user_id} from {start_date} to {end_date}")
            
            best_slots = []
            current_date = start_date
            
            while current_date <= end_date:
                # Check if this day is preferred
                if current_date.weekday() in preferred_days:
                    free_slots = self.find_free_slots(
                        user_id, 
                        current_date, 
                        duration_minutes,
                        preferred_hours['start'],
                        preferred_hours['end']
                    )
                    
                    # Add all available slots for this day (up to 3 per day)
                    for slot in free_slots[:3]:
                        best_slots.append({
                            'date': current_date.isoformat(),
                            'slot': slot,
                            'day_of_week': current_date.strftime('%A'),
                            'quality_score': self._calculate_slot_quality(slot, preferred_hours)
                        })
                
                current_date += timedelta(days=1)
            
            # Sort by quality score (higher is better)
            best_slots.sort(key=lambda x: x['quality_score'], reverse=True)
            
            print(f"Suggested {len(best_slots)} meeting time options")
            return best_slots[:10]  # Return top 10 suggestions
            
        except Exception as e:
            print(f"Error in suggest_meeting_time: {str(e)}")
            return []
    
    def _calculate_slot_quality(self, slot, preferred_hours):
        """Calculate a quality score for a time slot"""
        try:
            slot_start = datetime.fromisoformat(slot['start_time'])
            hour = slot_start.hour
            
            # Prefer times in the middle of preferred hours
            preferred_start = preferred_hours['start']
            preferred_end = preferred_hours['end']
            preferred_middle = (preferred_start + preferred_end) / 2
            
            # Calculate distance from preferred middle time
            distance_from_ideal = abs(hour - preferred_middle)
            
            # Score: higher is better (closer to ideal time)
            quality_score = 100 - (distance_from_ideal * 10)
            
            # Bonus for common meeting times
            if 10 <= hour <= 15:  # 10 AM to 3 PM
                quality_score += 20
            
            # Penalty for very early or very late
            if hour < 9 or hour > 16:
                quality_score -= 30
            
            return max(0, quality_score)
            
        except Exception as e:
            print(f"Error calculating slot quality: {str(e)}")
            return 50  # Default neutral score
    
    def get_calendar_summary(self, user_id, start_date=None, end_date=None):
        """Get a summary of calendar activity and conflicts
        
        This method now checks events from all CalendarConnections associated with the user,
        even if events were created under different user_ids (for backward compatibility).
        """
        try:
            from models.calendar_connection_model import CalendarConnection
            
            if not start_date:
                start_date = datetime.utcnow().date()
            if not end_date:
                end_date = start_date + timedelta(days=30)
            
            print(f"Generating calendar summary for user {user_id} from {start_date} to {end_date}")
            
            # Get all CalendarConnections for this user to find all connected account emails
            connections = CalendarConnection.query.filter_by(
                user_id=user_id,
                is_active=True,
                is_connected=True
            ).all()
            
            connected_emails = [conn.provider_account_email for conn in connections]
            connected_user_ids = [conn.user_id for conn in connections]
            connected_user_ids.append(user_id)  # Also include the main user_id
            connected_user_ids = list(set(connected_user_ids))  # Remove duplicates
            
            print(f"Found {len(connections)} active connections for user {user_id}")
            if connections:
                for conn in connections:
                    print(f"  - {conn.provider}: {conn.provider_account_email}")
            
            # Convert date range to datetime for query
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            # Get all events in the date range from all connected accounts
            if connected_emails:
                # Build OR conditions for matching events
                or_conditions = []
                
                # Match by user_id
                or_conditions.append(Event.user_id.in_(connected_user_ids))
                
                # Match by organizer email
                or_conditions.append(Event.organizer.in_(connected_emails))
                
                # Match by provider_event_id format: "email:event_id"
                for email in connected_emails:
                    or_conditions.append(Event.provider_event_id.like(f"{email}:%"))
                
                # Combine all OR conditions and filter by date range
                # Use broader filter to catch all events that overlap with the range
                events = Event.query.filter(
                    db.or_(*or_conditions),
                    Event.start_time < end_datetime,  # Event starts before range ends
                    Event.end_time > start_datetime    # Event ends after range starts
                ).all()
            else:
                # Fallback: just check by user_id
                # Use broader filter to catch all events that overlap with the range
                events = Event.query.filter(
                    Event.user_id == user_id,
                    Event.start_time < end_datetime,  # Event starts before range ends
                    Event.end_time > start_datetime    # Event ends after range starts
                ).all()
            
            print(f"Found {len(events)} events in date range from all connected accounts")

            # Exclude mirror blocker events (bidirectional sync placeholders)
            events = [
                event for event in events
                if not ((event.title or '').lower().startswith('[mirror]'))
            ]
            print(f"After removing mirror blockers: {len(events)} events")

            # Deduplicate events: Remove duplicates based on title (without [SYNCED] prefix), start_time, and organizer
            # This prevents counting the same event multiple times (e.g., original + synced version)
            seen_events = {}
            deduplicated_events = []
            for event in events:
                # Create a unique key based on title (without [SYNCED] prefix), start_time, and organizer
                title_key = event.title.replace('[SYNCED] ', '').strip()  # Remove [SYNCED] prefix for comparison
                event_key = (title_key, event.start_time, event.organizer)
                
                # Only add if we haven't seen this exact event before
                if event_key not in seen_events:
                    seen_events[event_key] = event
                    deduplicated_events.append(event)
                else:
                    # If duplicate found, prefer the one without [SYNCED] prefix (original)
                    existing_event = seen_events[event_key]
                    if '[SYNCED]' in event.title and '[SYNCED]' not in existing_event.title:
                        # Current event is synced, existing is original - keep existing
                        continue
                    elif '[SYNCED]' not in event.title and '[SYNCED]' in existing_event.title:
                        # Current event is original, existing is synced - replace
                        deduplicated_events.remove(existing_event)
                        seen_events[event_key] = event
                        deduplicated_events.append(event)
                    # If both are synced or both are original, keep the first one
            
            events = deduplicated_events
            print(f"After deduplication: {len(events)} unique events")
            
            # Calculate statistics
            total_events = len(events)
            events_with_conflicts = len([e for e in events if e.has_conflict])
            google_events = len([e for e in events if e.provider == 'google'])
            microsoft_events = len([e for e in events if e.provider == 'microsoft'])
            
            # Calculate total meeting time
            total_meeting_time = timedelta()
            for event in events:
                if not event.all_day:
                    total_meeting_time += event.end_time - event.start_time
            
            # Find busiest day
            daily_counts = {}
            for event in events:
                day = event.start_time.date()
                daily_counts[day] = daily_counts.get(day, 0) + 1
            
            busiest_day = max(daily_counts.items(), key=lambda x: x[1]) if daily_counts else None
            
            # Calculate average events per day
            date_range_days = (end_date - start_date).days + 1
            avg_events_per_day = total_events / date_range_days if date_range_days > 0 else 0
            
            # Convert events to dictionaries for frontend display
            events_list = []
            for event in sorted(events, key=lambda e: e.start_time, reverse=True):  # Most recent first
                event_dict = event.to_dict()
                # Add additional info for clarity
                event_dict['is_synced'] = '[SYNCED]' in event.title
                event_dict['display_title'] = event.title.replace('[SYNCED] ', '').strip()
                events_list.append(event_dict)
            
            summary = {
                'total_events': total_events,
                'events_with_conflicts': events_with_conflicts,
                'conflict_percentage': round((events_with_conflicts / total_events * 100), 2) if total_events > 0 else 0,
                'google_events': google_events,
                'microsoft_events': microsoft_events,
                'total_meeting_hours': round(total_meeting_time.total_seconds() / 3600, 2),
                'average_events_per_day': round(avg_events_per_day, 1),
                'busiest_day': {
                    'date': busiest_day[0].isoformat() if busiest_day else None,
                    'event_count': busiest_day[1] if busiest_day else 0
                },
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'provider_breakdown': {
                    'google_percentage': round((google_events / total_events * 100), 2) if total_events > 0 else 0,
                    'microsoft_percentage': round((microsoft_events / total_events * 100), 2) if total_events > 0 else 0
                },
                'events': events_list  # Include full event list for history display
            }
            
            print(f"Summary generated: {total_events} events, {events_with_conflicts} conflicts")
            return summary
            
        except Exception as e:
            print(f"Error in get_calendar_summary: {str(e)}")
            # Return a basic summary if there's an error
            return {
                'total_events': 0,
                'events_with_conflicts': 0,
                'conflict_percentage': 0,
                'google_events': 0,
                'microsoft_events': 0,
                'total_meeting_hours': 0,
                'average_events_per_day': 0,
                'busiest_day': {'date': None, 'event_count': 0},
                'date_range': {
                    'start': start_date.isoformat() if start_date else datetime.utcnow().date().isoformat(),
                    'end': end_date.isoformat() if end_date else (datetime.utcnow().date() + timedelta(days=30)).isoformat()
                },
                'provider_breakdown': {
                    'google_percentage': 0,
                    'microsoft_percentage': 0
                },
                'error': str(e)
            }