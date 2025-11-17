"""Dedicated Selenium flow for performing a clock-out."""

from __future__ import annotations

from dataclasses import dataclass

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from automation_shared import (
    should_use_headless,
    setup_driver,
    login,
    go_to_attendance,
)

CLOCK_OUT_BUTTON_1 = (By.ID, "ctl00_BodyContentPlaceHolder_navMarkOut")
CLOCK_OUT_BUTTON_2 = (By.ID, "ctl00_BodyContentPlaceHolder_btnAddNew")


def _perform_clock_out(driver, wait):
    """Execute the Selenium steps needed to clock out."""

    try:
        try:
            clock_out_btn_1 = wait.until(EC.element_to_be_clickable(CLOCK_OUT_BUTTON_1))
            clock_out_btn_1.click()
            print("First clock-out button clicked.")
        except Exception:
            print("First clock-out button not found, assuming we are on the correct page.")

        driver.implicitly_wait(0)
        clock_out_btn_2 = wait.until(EC.presence_of_element_located(CLOCK_OUT_BUTTON_2))
        driver.execute_script("arguments[0].scrollIntoView(true);", clock_out_btn_2)
        driver.execute_script("arguments[0].click();", clock_out_btn_2)
        print("Second clock-out button clicked.")

    finally:
        driver.implicitly_wait(5)


@dataclass
class ClockOutAutomation:
    """Encapsulates the Selenium session for clocking out."""

    headless: bool | None = None

    def run(self) -> dict:
        driver = None
        try:
            driver = setup_driver(headless_preference=should_use_headless(self.headless))
            wait = WebDriverWait(driver, 20)

            login(driver, wait)
            go_to_attendance(driver, wait)
            _perform_clock_out(driver, wait)

            return {
                "success": True,
                "message": "Clock-out completed successfully.",
            }

        except Exception as exc:
            if driver:
                driver.save_screenshot("error_clock_out.png")
            return {
                "success": False,
                "message": f"Clock-out failed: {exc}",
            }

        finally:
            if driver:
                driver.quit()
