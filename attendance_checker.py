from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime, date, time
import time as time_module
import re
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Import setup functions from automation.py
from automation_shared import setup_driver, login, go_to_attendance, should_use_headless

class AttendanceStatusChecker:
    def __init__(self):
        self.url = os.getenv("SPINE_URL")
        self.username = os.getenv("SPINE_USERNAME")
        self.password = os.getenv("SPINE_PASSWORD")

        # Locators for list view and attendance status
        self.LIST_VIEW_BUTTON = (By.XPATH, "//a[contains(@href, 'EmpAttendanceList') or contains(text(), 'List View') or contains(@title, 'List')]")
        self.ATTENDANCE_TABLE = (By.XPATH, "//table[contains(@class, 'table') or contains(@id, 'attendance')]")
        self.TODAY_ROW = (By.XPATH, "//tr[contains(., '{}')]".format(date.today().strftime('%d/%m/%Y')))

    def setup_headless_driver(self):
        """Set up a headless Chrome driver for background operations"""
        from selenium.webdriver.chrome.service import Service as ChromeService

        # Configure Chrome options for headless mode
        chrome_options = webdriver.ChromeOptions()

        # Headless mode
        chrome_options.add_argument("--headless=new")  # Use new headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # Camera permissions (even in headless mode)
        chrome_options.add_argument("--use-fake-ui-for-media-stream")
        chrome_options.add_argument("--use-fake-device-for-media-stream")
        chrome_options.add_argument("--use-fake-device-for-media-stream=black")

        # Additional options for stability
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Don't load images for speed
        # Note: JavaScript is enabled as Spine HR requires it
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Use ChromeDriver path from .env
        chromedriver_path = os.getenv("CHROMEDRIVER_PATH", "./chromedriver.exe")

        if chromedriver_path and os.path.exists(chromedriver_path):
            service = ChromeService(executable_path=chromedriver_path)
        else:
            # Let Selenium Manager handle it
            service = ChromeService()

        return webdriver.Chrome(service=service, options=chrome_options)

    def check_todays_attendance(self, headless=None):
        """Check today's actual attendance status from the system"""
        driver = None
        try:
            print("Checking today's attendance status...")

            use_headless = should_use_headless(headless)

            # Setup driver and login
            if use_headless:
                try:
                    driver = self.setup_headless_driver()
                    print("Running in headless mode...")
                except Exception as e:
                    logger.warning(f"Headless driver launch failed ({e}). Retrying with visible browser.")
                    driver = setup_driver()
                    print("Running with visible browser...")
            else:
                driver = setup_driver()
                print("Running with visible browser...")
            wait = WebDriverWait(driver, 20)

            # Login and navigate to attendance
            login(driver, wait)
            go_to_attendance(driver, wait)

            # Click on List View to see attendance records
            try:
                print("Navigating to attendance list view...")

                # Try to find list view button - it might have different text/attributes
                list_view_selectors = [
                    "//a[contains(text(), 'List View')]",
                    "//a[contains(text(), 'List')]",
                    "//a[contains(@href, 'List')]",
                    "//input[@value='List View']",
                    "//button[contains(text(), 'List')]",
                    "//a[contains(@title, 'List')]"
                ]

                list_view_clicked = False
                for selector in list_view_selectors:
                    try:
                        list_view_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        list_view_btn.click()
                        print(f"Success: Clicked list view button: {selector}")
                        list_view_clicked = True
                        break
                    except:
                        continue

                if not list_view_clicked:
                    print("Warning: Could not find list view button, trying to read current page...")

                # Wait for page to load
                time_module.sleep(3)

                # Look for today's attendance data
                attendance_status = self.parse_attendance_data(driver, wait)
                return attendance_status

            except Exception as e:
                print(f"Warning: Error navigating to list view: {e}")
                # Try to parse data from current page
                return self.parse_attendance_data(driver, wait)

        except Exception as e:
            logger.error(f"Error checking attendance status: {e}")
            return {
                'error': str(e),
                'clock_in_time': None,
                'clock_out_time': None,
                'status': 'unknown'
            }
        finally:
            if driver:
                driver.quit()

    def parse_attendance_data(self, driver, wait):
        """Parse attendance data from the current page"""
        try:
            today = date.today()
            today_str = today.strftime('%d/%m/%Y')
            today_alt_str = today.strftime('%d-%m-%Y')
            today_alt2_str = today.strftime('%Y-%m-%d')
            today_alt3_str = today.strftime('%d.%m.%Y')
            today_alt4_str = today.strftime('%m/%d/%Y')  # US format

            # Also try without leading zeros
            today_no_zero = f"{today.day}/{today.month}/{today.year}"
            today_no_zero2 = f"{today.day}-{today.month}-{today.year}"

            print(f"Looking for attendance data for {today_str} (and variants)...")
            print(f"Today's date: {today.strftime('%A, %B %d, %Y')}")

            # Try to find attendance table or data
            attendance_data = {
                'date': today_str,
                'clock_in_time': None,
                'clock_out_time': None,
                'status': 'not_found',
                'raw_data': None
            }

            # Look for various data structures - tables and timeline views
            data_selectors = [
                "//table",
                "//div[contains(@class, 'table')]",
                "//div[contains(@id, 'attendance')]",
                "//ul[contains(@class, 'timeline')]",  # Timeline structure
                "//div[contains(@id, 'divlistview')]",  # List view container
                "//div[contains(@class, 'timeline')]"
            ]

            for data_selector in data_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, data_selector)
                    for element in elements:
                        element_text = element.text.lower()

                        # Check if this element contains today's data
                        # Look for "today", actual dates, or times that suggest recent activity
                        if any(indicator in element_text for indicator in [
                            'today', 'in', 'out', 'clock',
                            today_str.lower(), today_alt_str.lower(), today_alt2_str.lower(),
                            today_alt3_str.lower(), today_no_zero, today_no_zero2,
                            str(today.day), str(today.month), str(today.year)
                        ]):
                            print(f"Found attendance data container: {data_selector}")
                            print(f"Content preview: {element_text[:200]}...")
                            attendance_data['raw_data'] = element.text

                            # Extract clock in/out times using regex
                            clock_times = self.extract_times_from_text(element.text)
                            attendance_data.update(clock_times)

                            # Additional check for timeline structure
                            timeline_times = self.extract_timeline_data(element)
                            if timeline_times['clock_in_time'] or timeline_times['clock_out_time']:
                                attendance_data.update(timeline_times)

                            attendance_data['status'] = 'found'
                            break

                    if attendance_data['status'] == 'found':
                        break

                except Exception as e:
                    continue

            # If no table found, try to get page content
            if attendance_data['status'] == 'not_found':
                try:
                    page_content = driver.find_element(By.TAG_NAME, "body").text
                    if any(date_str in page_content.lower() for date_str in [
                        today_str, today_alt_str, today_alt2_str, today_alt3_str,
                        today_no_zero, today_no_zero2, str(today.day), str(today.month)
                    ]):
                        print("Found today's data in page content")
                        attendance_data['raw_data'] = page_content
                        clock_times = self.extract_times_from_text(page_content)
                        attendance_data.update(clock_times)
                        attendance_data['status'] = 'found'
                except:
                    pass

            # Print what we found
            if attendance_data['status'] == 'found':
                print(f"Success: Today's attendance found:")
                print(f"   Clock In: {attendance_data['clock_in_time'] or 'Not recorded'}")
                print(f"   Clock Out: {attendance_data['clock_out_time'] or 'Not recorded'}")
            else:
                print("Error: No attendance data found for today")

            return attendance_data

        except Exception as e:
            logger.error(f"Error parsing attendance data: {e}")
            return {
                'error': str(e),
                'clock_in_time': None,
                'clock_out_time': None,
                'status': 'error'
            }

    def extract_times_from_text(self, text):
        """Extract clock in/out times from text using regex"""
        try:
            clock_data = {
                'clock_in_time': None,
                'clock_out_time': None
            }

            # Common time patterns (24-hour and 12-hour formats)
            time_patterns = [
                r'(\d{1,2}:\d{2}:\d{2})',  # HH:MM:SS
                r'(\d{1,2}:\d{2})',        # HH:MM
                r'(\d{1,2}\.\d{2})',       # HH.MM
                r'(\d{1,2}:\d{2}\s*[AP]M)',  # 12-hour format with AM/PM
            ]

            # Look for clock in patterns (improved for Spine HR format)
            clock_in_patterns = [
                r'(?:clock\s*in|in\s*time|start|entry)[\s:]*(\d{1,2}:\d{2}(?::\d{2})?\s*[AP]M)',
                r'(\d{1,2}:\d{2}(?::\d{2})?\s*[AP]M)[\s,]*(?:clock\s*in|in|entry|today)',
                r'in[\s:]*(\d{1,2}:\d{2}(?::\d{2})?\s*[AP]M)',
                r'(\d{1,2}:\d{2}\s*[AP]M)[\s,]*.*(?:in|today)',  # For "9:43 AM, Today"
                # Basic patterns without AM/PM
                r'(?:clock\s*in|in\s*time|start|entry)[\s:]*(\d{1,2}:\d{2}(?::\d{2})?)',
                r'in[\s:]+(\d{1,2}:\d{2}(?::\d{2})?)',
            ]

            # Look for clock out patterns (improved for Spine HR format)
            clock_out_patterns = [
                r'(?:clock\s*out|out\s*time|end|exit)[\s:]*(\d{1,2}:\d{2}(?::\d{2})?\s*[AP]M)',
                r'(\d{1,2}:\d{2}(?::\d{2})?\s*[AP]M)[\s,]*(?:clock\s*out|out|exit)',
                r'out[\s:]*(\d{1,2}:\d{2}(?::\d{2})?\s*[AP]M)',
                # Basic patterns without AM/PM
                r'(?:clock\s*out|out\s*time|end|exit)[\s:]*(\d{1,2}:\d{2}(?::\d{2})?)',
                r'out[\s:]+(\d{1,2}:\d{2}(?::\d{2})?)',
            ]

            text_lower = text.lower()

            # Extract clock in time
            for pattern in clock_in_patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    clock_data['clock_in_time'] = match.group(1)
                    break

            # Extract clock out time
            for pattern in clock_out_patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    clock_data['clock_out_time'] = match.group(1)
                    break

            # If specific patterns don't work, try to find all times and make educated guesses
            if not clock_data['clock_in_time'] and not clock_data['clock_out_time']:
                all_times = []
                for pattern in time_patterns:
                    matches = re.findall(pattern, text)
                    all_times.extend(matches)

                if all_times:
                    # Sort times to identify likely clock in (earliest) and clock out (latest)
                    try:
                        sorted_times = sorted(set(all_times))
                        if len(sorted_times) >= 1:
                            clock_data['clock_in_time'] = sorted_times[0]
                        if len(sorted_times) >= 2:
                            clock_data['clock_out_time'] = sorted_times[-1]
                    except:
                        pass

            return clock_data

        except Exception as e:
            logger.error(f"Error extracting times from text: {e}")
            return {
                'clock_in_time': None,
                'clock_out_time': None
            }

    def extract_timeline_data(self, element):
        """Extract clock times from timeline HTML structure"""
        try:
            clock_data = {
                'clock_in_time': None,
                'clock_out_time': None
            }

            # Look for timeline entries with Clock In/Out data
            timeline_items = element.find_elements(By.TAG_NAME, "li")

            for item in timeline_items:
                try:
                    item_text = item.text.lower()

                    # Check if this item contains clock in/out information
                    if 'in' in item_text or 'out' in item_text:
                        # Look for time spans within this item
                        time_spans = item.find_elements(By.TAG_NAME, "span")

                        for span in time_spans:
                            span_text = span.text.strip()

                            # Check if this span contains time data
                            if ':' in span_text and ('am' in span_text.lower() or 'pm' in span_text.lower()):
                                # Clean up the time string
                                time_str = span_text.replace(',', '').strip()

                                # Determine if this is clock in or out based on context
                                if 'in' in item_text and not clock_data['clock_in_time']:
                                    clock_data['clock_in_time'] = time_str
                                    print(f"Found Clock In: {time_str}")
                                elif 'out' in item_text and not clock_data['clock_out_time']:
                                    clock_data['clock_out_time'] = time_str
                                    print(f"Found Clock Out: {time_str}")

                except Exception as e:
                    continue

            return clock_data

        except Exception as e:
            logger.error(f"Error extracting timeline data: {e}")
            return {
                'clock_in_time': None,
                'clock_out_time': None
            }

    def save_attendance_screenshot(self, driver, filename="attendance_check.png"):
        """Save screenshot for debugging"""
        try:
            driver.save_screenshot(filename)
            print(f"Screenshot saved: {filename}")
        except Exception as e:
            logger.error(f"Error saving screenshot: {e}")

# Global instance
attendance_checker = AttendanceStatusChecker()

def check_current_attendance(headless=None):
    """Quick function to check current attendance status"""
    return attendance_checker.check_todays_attendance(headless=headless)

if __name__ == "__main__":
    # Test the attendance checker
    print("Testing Attendance Status Checker...")
    result = check_current_attendance()
    print("\nResult:", result)
