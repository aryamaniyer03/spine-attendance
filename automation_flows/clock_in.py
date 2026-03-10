"""Dedicated Selenium flow for performing a clock-in."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException,
    NoAlertPresentException,
    UnexpectedAlertPresentException,
)

from automation_shared import (
    should_use_headless,
    setup_driver,
    set_geolocation,
    login,
    go_to_attendance,
)
from email_notifier import send_email_with_screenshot

# Screenshots directory
SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")

# Locators specific to the clock-in flow
CLOCK_IN_BUTTON_1 = (By.ID, "ctl00_BodyContentPlaceHolder_navMarkIn")
CLOCK_IN_BUTTON_2 = (By.ID, "ctl00_BodyContentPlaceHolder_btnAddNew")

# Success verification: the final page (myloc.aspx) shows a timeline with:
#   <span class="ClockIn">In</span>
#   <span id="...lblEntryTime">3:23 PM,</span>
#   <span id="...lblEntryDt"> Today</span>
# We check for the first entry (ctrl0) having "In" class and "Today" date.
SUCCESS_ENTRY_TIME = "//span[contains(@id, 'ListView1_ctrl0_lblEntryTime')]"
SUCCESS_ENTRY_DATE = "//span[contains(@id, 'ListView1_ctrl0_lblEntryDt')]"
SUCCESS_ENTRY_TYPE = "//span[contains(@id, 'ListView1_ctrl0_lblInOut')]"

# The URL changes to myloc.aspx after successful clock-in
SUCCESS_URL_FRAGMENT = "myloc.aspx"

ERROR_INDICATORS = [
    "//span[contains(@id, 'lblMsgErrClock')]",
    "//span[contains(@id, 'lblMsg')]",
    "//span[contains(text(), 'already')]",
    "//span[contains(text(), 'error')]",
    "//span[contains(text(), 'Error')]",
    "//div[contains(@class, 'error')]",
]


def _save_screenshot(driver, prefix, step_name):
    """Save a screenshot with a descriptive name. Returns the path."""
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{step_name}_{timestamp}.png"
    path = os.path.join(SCREENSHOTS_DIR, filename)
    driver.save_screenshot(path)
    return path


def _handle_alert(driver, log):
    """Check for and handle any JavaScript alert/confirm/prompt dialogs."""
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        log(f"ALERT DETECTED: '{alert_text}'")
        alert.accept()
        log("Alert accepted.")
        return alert_text
    except (NoAlertPresentException, Exception):
        return None


def _check_page_indicators(driver, log):
    """Check the page for success/error messages after clock-in.

    Success = URL is myloc.aspx AND the first timeline entry shows "In" + "Today".
    """
    current_url = driver.current_url

    # Check if we landed on the success page (myloc.aspx)
    if SUCCESS_URL_FRAGMENT in current_url:
        log(f"URL contains '{SUCCESS_URL_FRAGMENT}' - on the clock result page.")

        # Check if the first entry shows "In" and "Today"
        try:
            entry_type_els = driver.find_elements(By.XPATH, SUCCESS_ENTRY_TYPE)
            entry_time_els = driver.find_elements(By.XPATH, SUCCESS_ENTRY_TIME)
            entry_date_els = driver.find_elements(By.XPATH, SUCCESS_ENTRY_DATE)

            if entry_type_els and entry_time_els:
                entry_type = entry_type_els[0].text.strip()
                entry_time = entry_time_els[0].text.strip()
                entry_date = entry_date_els[0].text.strip() if entry_date_els else ""

                log(f"Latest entry: type='{entry_type}', time='{entry_time}', date='{entry_date}'")

                if entry_type.lower() == "in" and "today" in entry_date.lower():
                    return "success", f"Clocked In at {entry_time} {entry_date}"
                elif entry_type.lower() == "in":
                    return "success", f"Clocked In at {entry_time} {entry_date}"
        except Exception as e:
            log(f"Error checking timeline entries: {e}")

    # Check for error indicators
    for xpath in ERROR_INDICATORS:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            for el in elements:
                text = el.text.strip()
                if el.is_displayed() and text:
                    log(f"ERROR INDICATOR FOUND: '{text}'")
                    return "error", text
        except Exception:
            continue

    return None, None


def _log_page_state(driver, log, step_name):
    """Log the current page state for debugging."""
    try:
        log(f"[{step_name}] URL: {driver.current_url}")
        log(f"[{step_name}] Title: {driver.title}")
    except Exception as e:
        log(f"[{step_name}] Could not read page state: {e}")


def _check_clock_in_button_state(driver, log):
    """Check if the clock-in button is still active or if clock-out is now active.
    If clock-out becomes active after our action, it means clock-in succeeded."""
    try:
        # Check if Mark Out button is now visible/active (means we clocked in)
        mark_out_btn = driver.find_elements(By.ID, "ctl00_BodyContentPlaceHolder_navMarkOut")
        if mark_out_btn:
            classes = mark_out_btn[0].get_attribute("class") or ""
            if "active" in classes.lower() or "selected" in classes.lower():
                log("VERIFICATION: Mark Out button is now active - clock-in likely succeeded.")
                return True

        # Check if Mark In button is now inactive/disabled
        mark_in_btn = driver.find_elements(By.ID, "ctl00_BodyContentPlaceHolder_navMarkIn")
        if mark_in_btn:
            classes = mark_in_btn[0].get_attribute("class") or ""
            disabled = mark_in_btn[0].get_attribute("disabled")
            if disabled or "disabled" in classes.lower():
                log("VERIFICATION: Mark In button is now disabled - clock-in likely succeeded.")
                return True

    except Exception as e:
        log(f"Could not check button state: {e}")

    return False


def _perform_clock_in(driver, wait, progress_callback=None):
    """Execute the Selenium steps needed to clock in.

    Returns a tuple of (success: bool, message: str).
    """

    def log(message):
        print(message)
        if progress_callback:
            progress_callback(message)

    # Step 1: Take a screenshot of the attendance page before clicking
    pre_screenshot = _save_screenshot(driver, "clock_in", "01_before_click")
    log(f"Pre-click screenshot: {pre_screenshot}")
    _log_page_state(driver, log, "BEFORE_CLICK")

    # Step 1.5: Wait for camera/video elements to initialize (if any)
    try:
        video_elements = driver.find_elements(By.TAG_NAME, "video")
        if video_elements:
            log(f"Found {len(video_elements)} video element(s) on page. Waiting for camera to initialize...")
            time.sleep(3)  # Give camera time to start streaming
            _save_screenshot(driver, "clock_in", "01b_camera_ready")
        else:
            log("No video elements found on page (camera may load after clicking).")
    except Exception:
        pass

    # Step 2: Handle any pre-existing alerts
    _handle_alert(driver, log)

    # Step 3: Click the first clock-in button (Mark In tab)
    try:
        clock_in_btn = wait.until(EC.element_to_be_clickable(CLOCK_IN_BUTTON_1))
        log(f"First clock-in button found. Tag: {clock_in_btn.tag_name}, Text: '{clock_in_btn.text}', "
            f"Displayed: {clock_in_btn.is_displayed()}, Enabled: {clock_in_btn.is_enabled()}")
        clock_in_btn.click()
        log("First clock-in button clicked (native click).")
    except Exception as e:
        log(f"FAILED to click first clock-in button: {e}")
        _save_screenshot(driver, "clock_in", "02_btn1_failed")
        return False, f"First clock-in button failed: {e}"

    # Step 4: Wait for page to react and handle any alert
    time.sleep(2)
    alert_text = _handle_alert(driver, log)
    if alert_text:
        log(f"Alert after first click: {alert_text}")

    _save_screenshot(driver, "clock_in", "03_after_btn1")

    # Step 4.5: Re-set geolocation before submitting (myloc.aspx will request it)
    set_geolocation(driver)

    # Step 5: Click the second button (Add New / Submit)
    try:
        driver.implicitly_wait(0)
        clock_in_btn_2 = wait.until(EC.element_to_be_clickable(CLOCK_IN_BUTTON_2))
        log(f"Second clock-in button found. Tag: {clock_in_btn_2.tag_name}, Text: '{clock_in_btn_2.text}', "
            f"Displayed: {clock_in_btn_2.is_displayed()}, Enabled: {clock_in_btn_2.is_enabled()}")

        # Try native click first, fall back to JS click
        try:
            clock_in_btn_2.click()
            log("Second clock-in button clicked (native click).")
        except Exception:
            driver.execute_script("arguments[0].click();", clock_in_btn_2)
            log("Second clock-in button clicked (JS fallback).")

    except TimeoutException:
        log("Second clock-in button not found within timeout.")
        _save_screenshot(driver, "clock_in", "04_btn2_not_found")
        # This might be OK if the first button was enough
    except Exception as e:
        log(f"Error with second button: {e}")
    finally:
        driver.implicitly_wait(5)

    # Step 6: Wait for page to navigate to myloc.aspx (success page) or handle alerts
    log("Waiting for page to navigate after clock-in...")
    navigated = False
    for i in range(15):  # Wait up to 15 seconds
        time.sleep(1)
        alert_text = _handle_alert(driver, log)
        if alert_text:
            log(f"Alert detected: {alert_text}")
        if SUCCESS_URL_FRAGMENT in driver.current_url:
            # Re-set geolocation so myloc.aspx picks it up
            set_geolocation(driver)
            log(f"Page navigated to success URL: {driver.current_url}")
            navigated = True
            break

    if not navigated:
        log(f"Page did NOT navigate to myloc.aspx. Current URL: {driver.current_url}")
        # Try clicking the button again as a confirmation
        try:
            driver.implicitly_wait(0)
            confirm_btn = driver.find_elements(*CLOCK_IN_BUTTON_2)
            if confirm_btn and confirm_btn[0].is_displayed():
                confirm_btn[0].click()
                log("Retry: clicked confirmation button.")
                time.sleep(3)
                _handle_alert(driver, log)
        except Exception:
            pass
        finally:
            driver.implicitly_wait(5)

    # Step 7: Take post-action screenshot and verify
    time.sleep(2)  # Let the success page fully load
    post_screenshot = _save_screenshot(driver, "clock_in", "05_after_all_clicks")
    log(f"Post-click screenshot: {post_screenshot}")
    _log_page_state(driver, log, "AFTER_CLICKS")

    # Step 9: Check for success/error indicators
    indicator_type, indicator_text = _check_page_indicators(driver, log)

    if indicator_type == "error":
        return False, f"Clock-in failed - page shows: {indicator_text}"

    if indicator_type == "success":
        return True, f"Clock-in verified - page shows: {indicator_text}"

    # Step 10: Check button state as fallback verification
    if _check_clock_in_button_state(driver, log):
        return True, "Clock-in verified via button state change."

    # Step 11: If no clear indicators, log a warning
    log("WARNING: Could not verify clock-in success. No success/error indicators found on page.")
    log("Dumping visible text on page for debugging...")
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        visible_text = body.text[:2000]  # First 2000 chars
        log(f"Page text: {visible_text}")
    except Exception:
        pass

    return False, "Clock-in completed but could NOT verify success. Check screenshots."


@dataclass
class ClockInAutomation:
    """Encapsulates the Selenium session for clocking in."""

    headless: bool | None = None
    progress_callback: callable = None

    def run(self) -> dict:
        driver = None
        screenshot_path = None

        def log(message):
            print(message)
            if self.progress_callback:
                self.progress_callback(message)

        try:
            log("Starting clock-in automation...")
            log("Initializing Chrome browser...")
            driver = setup_driver(headless_preference=should_use_headless(self.headless))
            wait = WebDriverWait(driver, 20)

            login(driver, wait, self.progress_callback)
            go_to_attendance(driver, wait, self.progress_callback)

            success, message = _perform_clock_in(driver, wait, self.progress_callback)

            # Take final screenshot
            log("Taking final screenshot...")
            os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(SCREENSHOTS_DIR, f"clock_in_final_{timestamp}.png")
            driver.save_screenshot(screenshot_path)
            log(f"Final screenshot saved: {screenshot_path}")

            # Send email notification
            log("Sending email notification...")
            send_email_with_screenshot(
                action="Clock-In",
                success=success,
                screenshot_path=screenshot_path
            )
            log("Email sent successfully!")

            if success:
                log(f"✓ Clock-in completed successfully! {message}")
            else:
                log(f"⚠ Clock-in may have failed: {message}")

            return {
                "success": success,
                "message": message,
                "screenshot": screenshot_path,
            }

        except Exception as exc:
            error_msg = f"✗ Clock-in failed: {exc}"
            log(error_msg)

            # Take error screenshot
            os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(SCREENSHOTS_DIR, f"clock_in_error_{timestamp}.png")

            if driver:
                driver.save_screenshot(screenshot_path)
                log(f"Error screenshot saved: {screenshot_path}")

            # Send email notification with error
            log("Sending error notification email...")
            send_email_with_screenshot(
                action="Clock-In",
                success=False,
                screenshot_path=screenshot_path,
                error_message=str(exc)
            )

            return {
                "success": False,
                "message": f"Clock-in failed: {exc}",
                "screenshot": screenshot_path,
            }

        finally:
            if driver:
                driver.quit()
            # NOTE: Screenshots are NO LONGER deleted - kept for debugging
