
"""Shared Selenium helpers and configuration for Spine automation flows."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.request
import zipfile
from typing import Optional

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    SessionNotCreatedException,
    TimeoutException,
)

load_dotenv()

URL = os.getenv("SPINE_URL", "https://msowinv.spinehrm.in/login.aspx?ReturnUrl=%2fhomepage.aspx")
USERNAME = os.getenv("SPINE_USERNAME")
PASSWORD = os.getenv("SPINE_PASSWORD")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")

CHROME_HEADLESS_DEFAULT = os.getenv("CHROME_HEADLESS", "true").strip().lower() in {"1", "true", "yes", "on"}

USERNAME_INPUT = (By.XPATH, "//input[@type='text' or (@name and contains(translate(@name,'USERNAME','username'),'user'))]")
PASSWORD_INPUT = (By.XPATH, "//input[@type='password']")
LOGIN_BUTTON_INPUT = (By.XPATH, "//input[@type='submit' and (contains(@value,'Login') or contains(@value,'LOGIN'))]")
LOGIN_BUTTON_BUTTON = (By.XPATH, "//button[(contains(text(),'Login') or contains(text(),'LOGIN'))]")

ATTENDANCE_BUTTON = (By.XPATH, "//a[contains(@href, 'EmpReqHome.aspx') and contains(text(), 'Atten.')]")


def should_use_headless(preference: Optional[bool] = None) -> bool:
    if preference is None:
        return CHROME_HEADLESS_DEFAULT
    return preference


def get_chrome_version() -> Optional[str]:
    try:
        if os.name == "nt":
            result = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    "(Get-Item \"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\").VersionInfo.ProductVersion",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        else:
            result = subprocess.run(["google-chrome", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip()
                return version.split()[-1]
    except Exception:
        pass
    return None


def get_chromedriver_version(chromedriver_path: str) -> Optional[str]:
    try:
        result = subprocess.run([chromedriver_path, "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            version_match = re.search(r"ChromeDriver (\\d+\\.\\d+\\.\\d+\\.\\d+)", result.stdout)
            if version_match:
                return version_match.group(1)
    except Exception:
        pass
    return None


def download_chromedriver(chrome_version: str, download_path: str) -> bool:
    try:
        major_version = chrome_version.split(".")[0]
        api_url = "https://googlechromelabs.github.io/chrome-for-testing/latest-versions-per-milestone.json"

        with urllib.request.urlopen(api_url) as response:
            data = json.loads(response.read().decode())

        if major_version not in data["milestones"]:
            return False

        chromedriver_version = data["milestones"][major_version]["version"]

        if os.name == "nt":
            download_url = f"https://storage.googleapis.com/chrome-for-testing-public/{chromedriver_version}/win64/chromedriver-win64.zip"
        else:
            download_url = f"https://storage.googleapis.com/chrome-for-testing-public/{chromedriver_version}/linux64/chromedriver-linux64.zip"

        print(f"Downloading ChromeDriver {chromedriver_version}...")

        zip_path = os.path.join(os.path.dirname(download_path), "chromedriver.zip")
        urllib.request.urlretrieve(download_url, zip_path)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(os.path.dirname(download_path))

        if os.name == "nt":
            extracted_path = os.path.join(os.path.dirname(download_path), "chromedriver-win64", "chromedriver.exe")
        else:
            extracted_path = os.path.join(os.path.dirname(download_path), "chromedriver-linux64", "chromedriver")

        if not os.path.exists(extracted_path):
            return False

        if os.path.exists(download_path):
            os.remove(download_path)

        import shutil

        shutil.move(extracted_path, download_path)

        if os.name != "nt":
            os.chmod(download_path, 0o755)

        os.remove(zip_path)
        extracted_dir = os.path.join(
            os.path.dirname(download_path), "chromedriver-win64" if os.name == "nt" else "chromedriver-linux64"
        )
        if os.path.exists(extracted_dir):
            shutil.rmtree(extracted_dir)

        print(f"ChromeDriver updated to version {chromedriver_version}")
        return True

    except Exception as exc:
        print(f"Error downloading ChromeDriver: {exc}")
        return False


def check_and_update_chromedriver(chromedriver_path: str) -> bool:
    if not chromedriver_path or not os.path.exists(chromedriver_path):
        return False

    chrome_version = get_chrome_version()
    chromedriver_version = get_chromedriver_version(chromedriver_path)

    if not chrome_version or not chromedriver_version:
        print("Could not detect Chrome or ChromeDriver version")
        return False

    if chrome_version.split(".")[0] != chromedriver_version.split(".")[0]:
        print(f"Version mismatch detected: Chrome {chrome_version} vs ChromeDriver {chromedriver_version}")
        print("Attempting to update ChromeDriver...")
        return download_chromedriver(chrome_version, download_path=chromedriver_path)

    print(f"ChromeDriver version {chromedriver_version} matches Chrome {chrome_version}")
    return True


def setup_driver(headless_preference: Optional[bool] = None) -> webdriver.Chrome:
    if headless_preference is None:
        use_headless = False
    else:
        use_headless = should_use_headless(headless_preference)

    chrome_options = webdriver.ChromeOptions()

    # Fake camera and media permissions
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    chrome_options.add_argument("--use-fake-device-for-media-stream")
    chrome_options.add_argument("--use-fake-device-for-media-stream=black")
    chrome_options.add_argument("--use-fake-device-for-media-stream=black=1280x720")

    # Allow location (will set custom coordinates) and other permissions
    prefs = {
        "profile.default_content_setting_values.geolocation": 1,  # 1=allow, 2=block
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_setting_values.media_stream_camera": 1,  # Allow fake camera
        "profile.default_content_setting_values.media_stream_mic": 1,  # Allow fake mic
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Set custom location (Mumbai, India by default - adjust as needed)
    # Latitude: 19.0760, Longitude: 72.8777 (Mumbai)
    chrome_options.add_experimental_option("prefs", {
        **prefs,
        "profile.content_settings.exceptions.geolocation": {
            "*": {"setting": 1}
        }
    })
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Additional arguments for cloud environments (Render, Heroku, etc.)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-setuid-sandbox")

    # Additional stability options for cloud environments
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--single-process")  # Run in single process mode for stability
    chrome_options.add_argument("--no-zygote")  # Disable zygote process

    if use_headless:
        # Use older headless mode for better compatibility in cloud environments
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    else:
        chrome_options.add_argument("--start-maximized")

    if CHROMEDRIVER_PATH and os.path.exists(CHROMEDRIVER_PATH):
        print(f"Using ChromeDriver from specified path: {CHROMEDRIVER_PATH}")
        if not check_and_update_chromedriver(CHROMEDRIVER_PATH):
            print("Warning: Could not verify or update ChromeDriver version")
        service = ChromeService(executable_path=CHROMEDRIVER_PATH)
    else:
        if CHROMEDRIVER_PATH:
            print(
                f"Warning: CHROMEDRIVER_PATH is set to '{CHROMEDRIVER_PATH}', but the file does not exist. "
                "Falling back to Selenium Manager."
            )
        else:
            print("CHROMEDRIVER_PATH not set. Relying on Selenium Manager to find the driver.")
        service = ChromeService()

    try:
        return webdriver.Chrome(service=service, options=chrome_options)
    except SessionNotCreatedException as exc:
        if "version" in str(exc).lower() and CHROMEDRIVER_PATH and os.path.exists(CHROMEDRIVER_PATH):
            print("ChromeDriver version mismatch detected. Attempting to auto-update...")
            chrome_version = get_chrome_version()
            if chrome_version and download_chromedriver(chrome_version, download_path=CHROMEDRIVER_PATH):
                print("ChromeDriver updated successfully. Retrying...")
                service = ChromeService(executable_path=CHROMEDRIVER_PATH)
                return webdriver.Chrome(service=service, options=chrome_options)
        raise


def login(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    # Set custom geolocation to user's location
    # Latitude: 23.034049, Longitude: 72.504524, Accuracy: 100
    try:
        driver.execute_cdp_cmd("Emulation.setGeolocationOverride", {
            "latitude": 23.034049,
            "longitude": 72.504524,
            "accuracy": 100
        })
        print("Geolocation set successfully.")
    except Exception as e:
        print(f"Warning: Could not set geolocation via CDP: {e}")

    print(f"Navigating to login page: {URL}")
    driver.get(URL)

    # Wait for page to load
    time.sleep(2)

    username_input = wait.until(EC.presence_of_element_located(USERNAME_INPUT))
    username_input.clear()
    username_input.send_keys(USERNAME)

    password_input = driver.find_element(*PASSWORD_INPUT)
    password_input.clear()
    password_input.send_keys(PASSWORD)

    try:
        login_btn = driver.find_element(*LOGIN_BUTTON_INPUT)
    except NoSuchElementException:
        login_btn = driver.find_element(*LOGIN_BUTTON_BUTTON)

    login_btn.click()
    print("Logged in successfully.")


def go_to_attendance(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    try:
        # Wait for page to stabilize after login
        time.sleep(2)

        # Ensure we're on the main content frame
        driver.switch_to.default_content()

        # Wait for the attendance button to be present and clickable
        print("Looking for attendance button...")
        attendance_btn = wait.until(EC.presence_of_element_located(ATTENDANCE_BUTTON))

        # Scroll button into view if needed
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", attendance_btn)
        time.sleep(0.5)

        # Wait for it to be clickable
        attendance_btn = wait.until(EC.element_to_be_clickable(ATTENDANCE_BUTTON))

        # Try JavaScript click first (more reliable in headless mode)
        try:
            driver.execute_script("arguments[0].click();", attendance_btn)
            print("Clicked attendance button using JavaScript.")
        except Exception:
            # Fallback to regular click
            attendance_btn.click()
            print("Clicked attendance button using regular click.")

        print("Navigated to attendance page.")
        time.sleep(1)
    except TimeoutException as exc:
        print(f"Timeout waiting for attendance button: {exc}")
        print(f"Current URL: {driver.current_url}")
        try:
            print(f"Page title: {driver.title}")
        except Exception:
            pass
        raise
    except Exception as exc:
        print(f"Error navigating to attendance page: {exc}")
        print(f"Current URL: {driver.current_url}")
        try:
            print(f"Page title: {driver.title}")
        except Exception:
            pass
        raise


def go_to_swipe_form(driver: webdriver.Chrome, wait: WebDriverWait, open_form: bool = True) -> None:
    print("Navigating to Swipe Request form...")
    time.sleep(0.3)

    original_handles = set(driver.window_handles)

    def switch_to_new_window() -> bool:
        current_handles = set(driver.window_handles)
        new_handles = current_handles - original_handles
        if new_handles:
            new_handle = new_handles.pop()
            driver.switch_to.window(new_handle)
            print("Switched to newly opened swipe window.")
            return True
        return False

    def switch_to_swipe_iframe() -> bool:
        driver.switch_to.default_content()
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for index, frame in enumerate(frames):
            try:
                driver.switch_to.frame(frame)
                if driver.find_elements(By.ID, "ctl00_BodyContentPlaceHolder_txtFromDate"):
                    print(f"Switched to swipe iframe (index {index}).")
                    return True
            except Exception:
                driver.switch_to.default_content()
                continue
            driver.switch_to.default_content()
        driver.switch_to.default_content()
        return False

    swipe_selectors = [
        "//a[contains(@href, 'AddSwipeRequest.aspx')]",
        "//a[contains(text(), 'Swipe')]",
        "//a[contains(text(), 'Apply')]",
        "//button[contains(text(), 'Swipe')]",
        "//span[contains(text(), 'Swipe')]/parent::a",
    ]

    button_found = False
    for selector in swipe_selectors:
        try:
            swipe_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
            swipe_btn.click()
            print(f"Successfully navigated to Swipe section using: {selector}")
            button_found = True
            break
        except Exception:
            continue

    if not button_found:
        print("Warning: Could not find Swipe button, trying direct URL...")
        current_url = driver.current_url
        base_url = current_url.split("/")[0] + "//" + current_url.split("/")[2]
        swipe_url = base_url + "/Atten/AddSwipeRequest.aspx"
        driver.get(swipe_url)
        print(f"Navigated to Swipe form via direct URL: {swipe_url}")

    if not open_form:
        time.sleep(0.2)
        return

    time.sleep(0.3)

    form_loaded = False
    try:
        wait.until(EC.presence_of_element_located((By.ID, "ctl00_BodyContentPlaceHolder_txtFromDate")))
        form_loaded = True
    except TimeoutException:
        pass

    if not form_loaded and switch_to_new_window():
        try:
            wait.until(EC.presence_of_element_located((By.ID, "ctl00_BodyContentPlaceHolder_txtFromDate")))
            form_loaded = True
        except TimeoutException:
            pass

    if not form_loaded and switch_to_swipe_iframe():
        try:
            wait.until(EC.presence_of_element_located((By.ID, "ctl00_BodyContentPlaceHolder_txtFromDate")))
            form_loaded = True
        except TimeoutException:
            pass

    if not form_loaded:
        apply_selectors = [
            "//button[contains(text(), 'Apply')]",
            "//a[contains(text(), 'Apply')]",
            "//input[@value='Apply']",
            "//a[contains(@id, 'btnAddNew')]",
            "//button[contains(@id, 'btnAddNew')]",
            "//span[contains(text(), 'Apply')]/ancestor::*[self::a or self::button]",
        ]

        for selector in apply_selectors:
            try:
                apply_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                apply_btn.click()
                print(f"Clicked secondary swipe action button: {selector}")
                switch_to_new_window()
                switch_to_swipe_iframe()
                wait.until(EC.presence_of_element_located((By.ID, "ctl00_BodyContentPlaceHolder_txtFromDate")))
                form_loaded = True
                break
            except TimeoutException:
                continue
            except Exception:
                continue

    if not form_loaded:
        print("Warning: Swipe form fields not detected after navigation.")
    else:
        print("Swipe request form ready for input.")

    time.sleep(0.5)


def go_to_recent_swipe_applications(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    print("Opening recent swipe applications...")
    driver.switch_to.default_content()

    recent_selectors = [
        "//a[contains(text(), 'Recent Applications')]",
        "//button[contains(text(), 'Recent Applications')]",
        "//span[contains(text(), 'Recent Applications')]/ancestor::*[self::a or self::button]",
        "//a[contains(@href, 'SwipeAppStatus')]",
    ]

    opened = False
    for selector in recent_selectors:
        try:
            recent_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
            recent_btn.click()
            print(f"Clicked recent applications control: {selector}")
            opened = True
            break
        except Exception:
            continue

    if not opened:
        raise RuntimeError("Could not locate Recent Applications link/button")

    # Some layouts require clicking an additional "Spine Status" tab/button
    status_selectors = [
        "//a[contains(text(), 'Spine Status')]",
        "//button[contains(text(), 'Spine Status')]",
        "//span[contains(text(), 'Spine Status')]/ancestor::*[self::a or self::button]",
    ]

    status_clicked = False
    for selector in status_selectors:
        try:
            status_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
            status_btn.click()
            print(f"Clicked status view control: {selector}")
            status_clicked = True
            break
        except Exception:
            continue

    driver.switch_to.default_content()
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for index, frame in enumerate(frames):
        try:
            driver.switch_to.frame(frame)
            if driver.find_elements(By.XPATH, "//table//tr[td]"):
                print(f"Recent applications loaded inside iframe index {index}.")
                break
        except Exception:
            driver.switch_to.default_content()
            continue
    else:
        driver.switch_to.default_content()

    wait.until(EC.presence_of_element_located((By.XPATH, "//table//tr[td]")))
    if status_clicked:
        print("Spine status table ready.")
    else:
        print("Recent applications page ready.")


__all__ = [
    "URL",
    "USERNAME",
    "PASSWORD",
    "should_use_headless",
    "setup_driver",
    "login",
    "go_to_attendance",
    "go_to_swipe_form",
    "go_to_recent_swipe_applications",
]
