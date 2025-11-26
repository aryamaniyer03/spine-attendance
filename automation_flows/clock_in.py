"""Dedicated Selenium flow for performing a clock-in."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from automation_shared import (
    should_use_headless,
    setup_driver,
    login,
    go_to_attendance,
)
from email_notifier import send_email_with_screenshot

# Locators specific to the clock-in flow
CLOCK_IN_BUTTON_1 = (By.ID, "ctl00_BodyContentPlaceHolder_navMarkIn")
CLOCK_IN_BUTTON_2 = (By.ID, "ctl00_BodyContentPlaceHolder_btnAddNew")


def _perform_clock_in(driver, wait, progress_callback=None):
    """Execute the Selenium steps needed to clock in."""

    def log(message):
        print(message)
        if progress_callback:
            progress_callback(message)

    try:
        try:
            clock_in_btn = wait.until(EC.element_to_be_clickable(CLOCK_IN_BUTTON_1))
            clock_in_btn.click()
            log("First clock-in button clicked.")
        except Exception:
            log("First clock-in button not found, trying second button...")

        driver.implicitly_wait(0)
        clock_in_btn_2 = wait.until(EC.presence_of_element_located(CLOCK_IN_BUTTON_2))
        driver.execute_script("arguments[0].scrollIntoView(true);", clock_in_btn_2)
        driver.execute_script("arguments[0].click();", clock_in_btn_2)
        log("Second clock-in button clicked.")

        try:
            clock_in_btn_2 = wait.until(EC.presence_of_element_located(CLOCK_IN_BUTTON_2))
            driver.execute_script("arguments[0].click();", clock_in_btn_2)
            log("Second clock-in button clicked again for confirmation.")
        except Exception:
            log("No confirmation needed or button not found.")

    finally:
        driver.implicitly_wait(5)


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
            _perform_clock_in(driver, wait, self.progress_callback)

            # Take final screenshot before closing
            log("Taking screenshot...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"clock_in_success_{timestamp}.png"
            driver.save_screenshot(screenshot_path)
            log(f"Screenshot saved: {screenshot_path}")
            
            # Send email notification
            log("Sending email notification...")
            send_email_with_screenshot(
                action="Clock-In",
                success=True,
                screenshot_path=screenshot_path
            )
            log("Email sent successfully!")

            log("✓ Clock-in completed successfully!")
            return {
                "success": True,
                "message": "Clock-in completed successfully.",
            }

        except Exception as exc:
            error_msg = f"✗ Clock-in failed: {exc}"
            log(error_msg)
            
            # Take error screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"clock_in_error_{timestamp}.png"
            
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
            }

        finally:
            if driver:
                driver.quit()
            
            # Clean up screenshot file after email is sent
            if screenshot_path and os.path.exists(screenshot_path):
                try:
                    os.remove(screenshot_path)
                    print(f"Screenshot cleaned up: {screenshot_path}")
                except Exception as e:
                    print(f"Failed to clean up screenshot: {e}")
