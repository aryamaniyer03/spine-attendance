"""Dedicated Selenium flow for performing a clock-out."""

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

CLOCK_OUT_BUTTON_1 = (By.ID, "ctl00_BodyContentPlaceHolder_navMarkOut")
CLOCK_OUT_BUTTON_2 = (By.ID, "ctl00_BodyContentPlaceHolder_btnAddNew")


def _perform_clock_out(driver, wait, progress_callback=None):
    """Execute the Selenium steps needed to clock out."""

    def log(message):
        print(message)
        if progress_callback:
            progress_callback(message)

    try:
        try:
            clock_out_btn_1 = wait.until(EC.element_to_be_clickable(CLOCK_OUT_BUTTON_1))
            clock_out_btn_1.click()
            log("First clock-out button clicked.")
        except Exception:
            log("First clock-out button not found, assuming we are on the correct page.")

        driver.implicitly_wait(0)
        clock_out_btn_2 = wait.until(EC.presence_of_element_located(CLOCK_OUT_BUTTON_2))
        driver.execute_script("arguments[0].scrollIntoView(true);", clock_out_btn_2)
        driver.execute_script("arguments[0].click();", clock_out_btn_2)
        log("Second clock-out button clicked.")

        try:
            clock_out_btn_2 = wait.until(EC.presence_of_element_located(CLOCK_OUT_BUTTON_2))
            driver.execute_script("arguments[0].click();", clock_out_btn_2)
            log("Second clock-out button clicked again for confirmation.")
        except Exception:
            log("No confirmation needed for clock-out or button not found.")

    finally:
        driver.implicitly_wait(5)


@dataclass
class ClockOutAutomation:
    """Encapsulates the Selenium session for clocking out."""

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
            log("Starting clock-out automation...")
            log("Initializing Chrome browser...")
            driver = setup_driver(headless_preference=should_use_headless(self.headless))
            wait = WebDriverWait(driver, 20)

            login(driver, wait, self.progress_callback)
            go_to_attendance(driver, wait, self.progress_callback)
            _perform_clock_out(driver, wait, self.progress_callback)

            # Take final screenshot before closing
            log("Taking screenshot...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"clock_out_success_{timestamp}.png"
            driver.save_screenshot(screenshot_path)
            log(f"Screenshot saved: {screenshot_path}")
            
            # Send email notification
            log("Sending email notification...")
            send_email_with_screenshot(
                action="Clock-Out",
                success=True,
                screenshot_path=screenshot_path
            )
            log("Email sent successfully!")

            log("✓ Clock-out completed successfully!")
            return {
                "success": True,
                "message": "Clock-out completed successfully.",
            }

        except Exception as exc:
            error_msg = f"✗ Clock-out failed: {exc}"
            log(error_msg)
            
            # Take error screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"clock_out_error_{timestamp}.png"
            
            if driver:
                driver.save_screenshot(screenshot_path)
                log(f"Error screenshot saved: {screenshot_path}")
            
            # Send email notification with error
            log("Sending error notification email...")
            send_email_with_screenshot(
                action="Clock-Out",
                success=False,
                screenshot_path=screenshot_path,
                error_message=str(exc)
            )
            
            return {
                "success": False,
                "message": f"Clock-out failed: {exc}",
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
