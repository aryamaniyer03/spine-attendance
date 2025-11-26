import asyncio
import logging
from datetime import datetime, date, time, timedelta
from attendance_checker import attendance_checker
from attendance_analyzer import attendance_analyzer
from chatgpt_assistant import ChatGPTAssistant
from automation_shared import should_use_headless
import schedule

logger = logging.getLogger(__name__)

class SystemInitializer:
    def __init__(self, smart_attendance):
        self.smart_attendance = smart_attendance
        self.chatgpt_assistant = None

    async def initialize_system(self):
        """Initialize the system with actual attendance checking and intelligent scheduling"""
        try:
            print("Starting Smart Attendance...")

            # Step 1: Initialize ChatGPT Assistant
            await self.initialize_chatgpt()

            # Step 2: Check if today is a working day
            if self.smart_attendance.should_skip_today():
                await self.handle_non_working_day()
                return

            # Step 3: Check actual attendance status
            attendance_status = await self.check_actual_attendance()

            # Step 4: Analyze missing attendance and suggest swipes
            await self.check_missing_attendance()

            # Step 5: Set up intelligent scheduling based on actual status
            await self.setup_intelligent_schedule(attendance_status)

            print("Smart Attendance ready.")

        except Exception as e:
            logger.error(f"Error during system initialization: {e}")
            print(f"❌ System initialization failed: {e}")

    async def initialize_chatgpt(self):
        """Initialize ChatGPT assistant"""
        try:
            print("Bringing up ChatGPT assistant...")

            # Initialize ChatGPT assistant
            self.chatgpt_assistant = ChatGPTAssistant(self.smart_attendance)

            # Set global assistant
            from chatgpt_assistant import set_assistant
            set_assistant(self.chatgpt_assistant)

            print("ChatGPT assistant connected.")

        except Exception as e:
            logger.error(f"Error initializing ChatGPT: {e}")
            print(f"ChatGPT assistant unavailable: {e}")
            print("Check OPENAI_API_KEY in .env if you need AI replies.")

    async def handle_non_working_day(self):
        """Handle non-working days (holidays/weekends)"""
        try:
            today = date.today()
            print(f"No work scheduled for {today.strftime('%B %d, %Y')}")

            if self.smart_attendance.is_holiday():
                message_type = "holiday"
            elif self.smart_attendance.is_weekend():
                message_type = "weekend"
            else:
                message_type = "day off"

            # Send natural notification if ChatGPT is available
            if self.chatgpt_assistant:
                message = await self.chatgpt_assistant.generate_reminder_message("no_work")
                await self.send_notification(message)
            else:
                await self.send_notification(f"Enjoy the {message_type}! I'm on standby if you need anything.")

        except Exception as e:
            logger.error(f"Error handling non-working day: {e}")

    async def check_actual_attendance(self):
        """Check actual attendance status from the system"""
        try:
            print("Checking actual attendance status...")

            # Run attendance check in a separate thread to avoid blocking
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(attendance_checker.check_todays_attendance, should_use_headless())
                attendance_status = future.result(timeout=60)  # 60 second timeout

            if attendance_status.get('error'):
                print(f"Warning: Error checking attendance: {attendance_status['error']}")
                return None

            # Parse the results
            clock_in_time = attendance_status.get('clock_in_time')
            clock_out_time = attendance_status.get('clock_out_time')

            print("\nActual Attendance Status:")
            print(f"   Clock In:  {clock_in_time or 'Not recorded'}")
            print(f"   Clock Out: {clock_out_time or 'Not recorded'}")

            return attendance_status

        except Exception as e:
            logger.error(f"Error checking actual attendance: {e}")
            print(f"Warning: Could not check actual attendance: {e}")
            return None

    async def check_missing_attendance(self):
        """Check for missing attendance and suggest swipe requests"""
        try:
            print("Analyzing attendance gaps for missing days...")

            # Run attendance analysis in a separate thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Check last 30 days for missing attendance
                end_date = date.today() - timedelta(days=1)  # Exclude today
                start_date = end_date - timedelta(days=30)   # Last 30 working days

                future = executor.submit(
                    attendance_analyzer.analyze_attendance_gaps,
                    start_date, end_date, should_use_headless()
                )
                analysis_result = future.result(timeout=90)  # 90 second timeout

            if analysis_result.get('error'):
                print(f"Warning: Error analyzing attendance: {analysis_result['error']}")
                return

            missing_count = analysis_result.get('total_missing_days', 0)
            missing_dates = analysis_result.get('missing_dates', [])

            swipe_applications = []
            try:
                swipe_applications = get_recent_swipe_applications(
                    limit=50, headless=should_use_headless()
                )
            except Exception as fetch_err:
                logger.warning(f"Could not retrieve recent swipe applications: {fetch_err}")

            swipe_by_date = {}
            for entry in swipe_applications:
                swipe_by_date.setdefault(entry['date'], entry)

            matched_swipes = [entry for entry in swipe_applications if entry['date'] in missing_dates]
            missing_without_swipes = [d for d in missing_dates if d not in swipe_by_date]

            print("Attendance gap check completed.")
            print(f"Missing days detected: {missing_count}")

            if matched_swipes:
                print("Swipe requests already on file for:")
                for entry in matched_swipes[:5]:
                    print(f" - {entry['date'].strftime('%d-%b-%Y')}: {entry['status'] or 'Status unknown'}")

            if missing_without_swipes:
                print("Missing attendance with no swipe recorded:")
                for entry in missing_without_swipes[:5]:
                    print(f" - {entry.strftime('%d-%b-%Y (%A)')}")

            if missing_count > 0:
                recent_missing = sorted(missing_dates, reverse=True)[:5]

                if self.chatgpt_assistant:
                    suggestions = analysis_result.get('suggestions', [])
                    status_highlights = []
                    for entry in matched_swipes[:3]:
                        status_highlights.append(
                            f"Swipe on {entry['date'].strftime('%d-%b')}: {entry['status'] or 'Status unknown'}"
                        )
                    if missing_without_swipes:
                        highlight = ", ".join(d.strftime('%d-%b') for d in missing_without_swipes[:3])
                        status_highlights.insert(0, f"No swipe yet for {highlight}")
                    if status_highlights:
                        suggestions = status_highlights + suggestions

                    message = await self.chatgpt_assistant.generate_swipe_notification(
                        missing_count, recent_missing, suggestions
                    )
                else:
                    if missing_without_swipes:
                        missing_summary = ", ".join(
                            d.strftime('%d-%b') for d in missing_without_swipes[:3]
                        )
                        missing_line = (
                            f"No swipe recorded yet for {missing_summary}"
                            + (" and others." if len(missing_without_swipes) > 3 else ".")
                        )
                    else:
                        existing_summary = ", ".join(
                            f"{entry['date'].strftime('%d-%b')} ({entry['status'] or 'Status unknown'})"
                            for entry in matched_swipes[:3]
                        )
                        missing_line = (
                            "All missing days already have swipe requests on file"
                            + (f": {existing_summary}." if existing_summary else ".")
                        )

                    if missing_count == 1:
                        date_str = recent_missing[0].strftime('%d-%b-%Y')
                        message = (
                            f"Heads-up: you're missing attendance for {date_str}. {missing_line} "
                            "Say 'Apply swipe for [date] - reason' if you'd like me to file one."
                        )
                    else:
                        message = (
                            f"You're short on {missing_count} attendance days. {missing_line} "
                            "Say 'Fill missing swipes - reason' and I'll take care of them."
                        )

                await self.send_notification(message)
            else:
                print("No missing attendance found.")

        except Exception as e:
            logger.error(f"Error checking missing attendance: {e}")
            print(f"Warning: Could not check missing attendance: {e}")

    async def setup_intelligent_schedule(self, attendance_status):
        """Set up intelligent scheduling based on actual attendance status"""
        try:
            today = date.today()
            now = datetime.now()

            print("Setting up today's schedule...")

            # Determine current attendance state
            has_clocked_in = attendance_status and attendance_status.get('clock_in_time')
            has_clocked_out = attendance_status and attendance_status.get('clock_out_time')

            if has_clocked_out:
                # Already completed work for today
                print("Workday already wrapped up.")
                await self.send_notification("Nice work—today's attendance is already complete.")
                return

            elif has_clocked_in:
                # Already clocked in, need to schedule clock out
                actual_clock_in = attendance_status.get('clock_in_time')
                print(f"Already clocked in at {actual_clock_in}")

                # Calculate when to clock out (9-9.5 hours later)
                clock_out_time = self.calculate_clock_out_time(actual_clock_in)

                if clock_out_time and clock_out_time > now.time():
                    # Schedule clock out
                    self.smart_attendance.clock_in_time = self.parse_time(actual_clock_in)
                    self.smart_attendance.clock_out_time = clock_out_time
                    self.smart_attendance.should_work_today = True

                    # Schedule the clock out
                    schedule.every().day.at(clock_out_time.strftime("%H:%M")).do(
                        self.smart_attendance.perform_clock_out
                    ).tag('today_attendance')

                    # Schedule reminder 5 minutes before
                    reminder_time = (datetime.combine(today, clock_out_time) - timedelta(minutes=5)).time()
                    schedule.every().day.at(reminder_time.strftime("%H:%M")).do(
                        self.smart_attendance.send_clock_out_reminder_sync
                    ).tag('today_attendance')

                    print(f"Clock-out scheduled for {clock_out_time.strftime('%H:%M')}")

                    # Send natural notification
                    if self.chatgpt_assistant:
                        message = await self.chatgpt_assistant.generate_reminder_message(
                            "daily_schedule", clock_out_time.strftime('%H:%M')
                        )
                    else:
                        message = f"Clock-out is set for {clock_out_time.strftime('%H:%M')}. Let me know if you'd like it adjusted."

                    await self.send_notification(message)
                else:
                    print("⚠️ Clock out time has already passed or couldn't be calculated")

            else:
                # Haven't clocked in yet, set up full day schedule
                print("Scheduling today's attendance window.")

                # Generate random times for today
                self.smart_attendance.should_work_today = True
                self.smart_attendance.schedule_today_attendance()

                # Send natural morning notification
                if self.chatgpt_assistant:
                    message = await self.chatgpt_assistant.generate_reminder_message("daily_schedule")
                else:
                    clock_in_str = self.smart_attendance.clock_in_time.strftime('%H:%M')
                    clock_out_str = self.smart_attendance.clock_out_time.strftime('%H:%M')
                    message = (
                        f"Morning! I'll aim for a {clock_in_str} start and {clock_out_str} wrap. Ping me if you need a different plan."
                    )

                await self.send_notification(message)

        except Exception as e:
            logger.error(f"Error setting up intelligent schedule: {e}")
            print(f"⚠️ Error setting up schedule: {e}")

    def calculate_clock_out_time(self, clock_in_str):
        """Calculate clock out time based on actual clock in time"""
        try:
            # Parse the clock in time
            clock_in_time = self.parse_time(clock_in_str)
            if not clock_in_time:
                return None

            # Add 9-9.5 hours (randomly choose within range)
            import random
            work_minutes = random.randint(540, 570)  # 9.0 to 9.5 hours in minutes
            print(f"Random work duration selected: {work_minutes} minutes ({work_minutes/60:.1f} hours)")

            # Calculate clock out time
            clock_in_datetime = datetime.combine(date.today(), clock_in_time)
            clock_out_datetime = clock_in_datetime + timedelta(minutes=work_minutes)

            return clock_out_datetime.time()

        except Exception as e:
            logger.error(f"Error calculating clock out time: {e}")
            return None

    def parse_time(self, time_str):
        """Parse time string into time object"""
        try:
            # Handle various time formats
            time_formats = [
                "%H:%M:%S",
                "%H:%M",
                "%I:%M:%S %p",
                "%I:%M %p"
            ]

            for fmt in time_formats:
                try:
                    parsed_datetime = datetime.strptime(time_str, fmt)
                    return parsed_datetime.time()
                except ValueError:
                    continue

            return None

        except Exception as e:
            logger.error(f"Error parsing time: {e}")
            return None

    async def send_notification(self, message):
        """Send notification via Telegram bot"""
        try:
            from telegram_bot import get_bot

            bot = get_bot()
            if bot:
                await bot.broadcast_notification(message)
            else:
                print(f"📱 Notification: {message}")

        except Exception as e:
            logger.error(f"Error sending notification: {e}")

    async def daily_health_check(self):
        """Perform daily health check and system optimization"""
        try:
            print("🔧 Performing daily health check...")

            # Check if schedules are still valid
            today = date.today()
            current_jobs = schedule.jobs

            print(f"📋 Current scheduled jobs: {len(current_jobs)}")

            # Clean up old jobs
            for job in current_jobs:
                if hasattr(job, 'tags') and 'today_attendance' in job.tags:
                    print(f"   - {job.job_func.__name__} at {job.next_run}")

            # Check system components
            components_status = {
                'Smart Attendance': self.smart_attendance is not None,
                'ChatGPT Assistant': self.chatgpt_assistant is not None,
                'Telegram Bot': True,  # Will be checked separately
                'Scheduler': len(current_jobs) > 0
            }

            print("🚥 System Components Status:")
            for component, status in components_status.items():
                status_icon = "✅" if status else "❌"
                print(f"   {status_icon} {component}")

            return components_status

        except Exception as e:
            logger.error(f"Error in daily health check: {e}")
            return {}

# Global system initializer
system_initializer = None

def get_initializer():
    """Get the global system initializer instance"""
    return system_initializer

def set_initializer(initializer):
    """Set the global system initializer instance"""
    global system_initializer
    system_initializer = initializer
