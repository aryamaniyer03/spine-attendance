from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from datetime import datetime, date, timedelta
import time
import os
import logging
from urllib.parse import urlsplit
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Import setup functions shared across flows
from automation_shared import (
    setup_driver,
    login,
    URL,
    go_to_attendance,
    go_to_swipe_form,
    go_to_recent_swipe_applications,
    should_use_headless,
)

class SwipeRequestManager:
    def __init__(self):
        self.url = os.getenv("SPINE_URL")
        self.username = os.getenv("SPINE_USERNAME")
        self.password = os.getenv("SPINE_PASSWORD")

        # Form field locators based on HTML analysis
        self.FORM_FIELDS = {
            'category': (By.ID, "ctl00_BodyContentPlaceHolder_drpSwipeCategory"),
            'date': (By.ID, "ctl00_BodyContentPlaceHolder_txtFromDate"),
            'in_out_type': (By.ID, "ctl00_BodyContentPlaceHolder_dpInout"),
            'in_time': (By.ID, "ctl00_BodyContentPlaceHolder_txtInTime"),
            'out_time': (By.ID, "ctl00_BodyContentPlaceHolder_txtOuttime"),
            'reason': (By.ID, "ctl00_BodyContentPlaceHolder_txtReason"),
            'save_button': (By.ID, "ctl00_BodyContentPlaceHolder_btnSave"),
            'cancel_button': (By.ID, "ctl00_BodyContentPlaceHolder_btnCancel"),
            'error_message': (By.ID, "ctl00_BodyContentPlaceHolder_lblErrMsg"),
            'success_message': (By.ID, "ctl00_BodyContentPlaceHolder_lblMsg")
        }

        # Default shift timings
        self.DEFAULT_SHIFT = {
            'in_time': '9:00 AM',
            'out_time': '6:00 PM'
        }

    DATE_PATTERNS = [
        "%d-%b-%Y",
        "%d-%b-%y",
        "%d/%m/%Y",
        "%d/%m/%y",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%Y-%m-%d",
        "%d %b %Y",
        "%d %B %Y",
    ]

    def setup_headless_driver(self):
        """Set up a headless Chrome driver for background operations"""
        from selenium.webdriver.chrome.service import Service as ChromeService

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--use-fake-ui-for-media-stream")
        chrome_options.add_argument("--use-fake-device-for-media-stream")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        chromedriver_path = os.getenv("CHROMEDRIVER_PATH", "./chromedriver.exe")
        if chromedriver_path and os.path.exists(chromedriver_path):
            service = ChromeService(executable_path=chromedriver_path)
        else:
            service = ChromeService()

        return webdriver.Chrome(service=service, options=chrome_options)

    def submit_single_swipe(self, swipe_date, reason, in_time=None, out_time=None,
                           swipe_type='both', category='Regularization', headless=None):
        """Submit a single swipe request"""
        driver = None
        try:
            print(f"Submitting swipe request for {swipe_date.strftime('%d-%b-%Y')}...")

            use_headless = should_use_headless(headless)

            # Setup driver and login
            if use_headless:
                try:
                    driver = self.setup_headless_driver()
                    print("Running swipe submission in headless mode...")
                except Exception as e:
                    logger.warning(f"Headless swipe submission failed ({e}). Retrying with visible browser.")
                    driver = setup_driver()
                    print("Running swipe submission with visible browser...")
            else:
                driver = setup_driver()
                print("Running swipe submission with visible browser...")
            wait = WebDriverWait(driver, 15)

            # Login and navigate to swipe form
            login(driver, wait)
            go_to_swipe_form(driver, wait, open_form=True)

            # Fill the form
            result = self.fill_swipe_form(driver, wait, swipe_date, reason,
                                        in_time, out_time, swipe_type, category)

            if result['success']:
                print(f"Successfully submitted swipe for {swipe_date.strftime('%d-%b-%Y')}")
            else:
                print(f"Failed to submit swipe: {result['message']}")

            return result

        except Exception as e:
            logger.error(f"Error submitting swipe request: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'date': swipe_date
            }
        finally:
            if driver:
                driver.quit()

    def parse_date_string(self, text):
        text = text.strip()
        for fmt in self.DATE_PATTERNS:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    def fetch_recent_swipe_applications(self, limit=20, headless=None):
        """Return recent swipe applications with their statuses."""
        driver = None
        entries = []

        try:
            use_headless = should_use_headless(headless)

            if use_headless:
                try:
                    driver = self.setup_headless_driver()
                    print("Fetching recent swipe applications in headless mode...")
                except Exception as e:
                    logger.warning(f"Headless recent applications failed ({e}). Switching to visible mode.")
                    driver = setup_driver()
            else:
                driver = setup_driver()

            wait = WebDriverWait(driver, 15)

            login(driver, wait)
            go_to_swipe_form(driver, wait, open_form=True)

            try:
                recent_btn = wait.until(
                    EC.element_to_be_clickable((By.ID, "ctl00_BodyContentPlaceHolder_navRecent"))
                )
                driver.execute_script("arguments[0].click();", recent_btn)
                print("Opened Recent Applications via navRecent button.")
            except Exception as nav_err:
                print(f"Falling back to legacy navigation for Recent Applications: {nav_err}")
                go_to_recent_swipe_applications(driver, wait)

            driver.switch_to.default_content()
            try:
                wait.until(EC.presence_of_element_located((By.ID, "ctl00_BodyContentPlaceHolder_ListView1_ctrl0_divBox")))
            except TimeoutException:
                print("Recent applications list not found.")
                return []
            cards = driver.find_elements(By.CSS_SELECTOR, "div[id^='ctl00_BodyContentPlaceHolder_ListView1_ctrl'][id$='_divBox']")

            for card in cards:
                try:
                    date_text = card.find_element(By.CSS_SELECTOR, "span[id$='_lblFromDate']").text.strip()
                    date_obj = self.parse_date_string(date_text)
                except Exception:
                    continue

                day_text = ""
                try:
                    day_text = card.find_element(By.CSS_SELECTOR, "span[id$='_lblDay']").text.strip()
                except Exception:
                    pass

                reason_text = ""
                try:
                    reason_text = card.find_element(By.CSS_SELECTOR, "div.remarks").text.strip()
                except Exception:
                    pass

                in_time = ""
                out_time = ""
                try:
                    in_time = card.find_element(By.CSS_SELECTOR, "span[id$='_lblInTime']").text.strip()
                except Exception:
                    pass
                try:
                    out_time = card.find_element(By.CSS_SELECTOR, "span[id$='_lblOutTime']").text.strip()
                except Exception:
                    pass

                req_type = ""
                try:
                    req_type = card.find_element(By.CSS_SELECTOR, "span[id$='_lblReqType']").text.strip()
                except Exception:
                    pass

                status_indicator = ""
                try:
                    status_indicator = card.find_element(By.CSS_SELECTOR, ".leaveBlockOne").get_attribute("class")
                except Exception:
                    pass

                entry = {
                    'date': date_obj,
                    'date_raw': date_text,
                    'weekday': day_text,
                    'in_time': in_time,
                    'out_time': out_time,
                    'reason': reason_text,
                    'request_type': req_type,
                    'status_indicator': status_indicator,
                }

                entries.append(entry)

                if limit and len(entries) >= limit:
                    break

            print(f"Collected {len(entries)} recent swipe application(s).")
            return entries

        except Exception as e:
            logger.error(f"Error fetching recent swipe applications: {e}")
            return []
        finally:
            if driver:
                driver.quit()

    def submit_batch_swipes(self, date_list, reason, in_time=None, out_time=None,
                           swipe_type='both', category='Regularization', headless=None):
        """Submit multiple swipe requests in batch"""
        driver = None
        results = []

        try:
            print(f"Submitting batch swipe requests for {len(date_list)} dates...")

            use_headless = should_use_headless(headless)

            # Setup driver and login once for all requests
            if use_headless:
                try:
                    driver = self.setup_headless_driver()
                    print("Running batch swipe submission in headless mode...")
                except Exception as e:
                    logger.warning(f"Headless batch swipe failed ({e}). Retrying with visible browser.")
                    driver = setup_driver()
                    print("Running batch swipe submission with visible browser...")
            else:
                driver = setup_driver()
                print("Running batch swipe submission with visible browser...")
            wait = WebDriverWait(driver, 15)

            # Login once
            login(driver, wait)

            # Process each date
            for i, swipe_date in enumerate(date_list):
                try:
                    print(f"Processing {i+1}/{len(date_list)}: {swipe_date.strftime('%d-%b-%Y')}")

                    # Navigate to swipe form
                    go_to_swipe_form(driver, wait)

                    # Fill and submit the form
                    result = self.fill_swipe_form(driver, wait, swipe_date, reason,
                                                in_time, out_time, swipe_type, category)

                    result['date'] = swipe_date
                    results.append(result)

                    if result['success']:
                        print(f"Success: {swipe_date.strftime('%d-%b-%Y')}")
                    else:
                        print(f"Failed: {swipe_date.strftime('%d-%b-%Y')} - {result['message']}")

                    # Minimal delay between requests
                    time.sleep(0.3)

                except Exception as e:
                    error_result = {
                        'success': False,
                        'message': f"Error processing {swipe_date}: {str(e)}",
                        'date': swipe_date
                    }
                    results.append(error_result)
                    print(f"Error with {swipe_date.strftime('%d-%b-%Y')}: {e}")

            return self.summarize_batch_results(results)

        except Exception as e:
            logger.error(f"Error in batch swipe submission: {e}")
            return {
                'success': False,
                'message': f"Batch error: {str(e)}",
                'results': results
            }
        finally:
            if driver:
                driver.quit()

    def fill_swipe_form(self, driver, wait, swipe_date, reason, in_time=None,
                       out_time=None, swipe_type='both', category='Regularization'):
        """Fill and submit the swipe request form"""
        try:
            # Set default times if not provided
            if not in_time:
                in_time = self.DEFAULT_SHIFT['in_time']
            if not out_time:
                out_time = self.DEFAULT_SHIFT['out_time']

            # Format date for the form (dd-MMM-yy)
            formatted_date = swipe_date.strftime("%d-%b-%y")

            # Small delay to ensure form is fully loaded after context switch
            time.sleep(0.2)

            # Clear any existing error messages
            try:
                error_elem = driver.find_element(*self.FORM_FIELDS['error_message'])
                driver.execute_script("arguments[0].innerHTML = '';", error_elem)
            except:
                pass

            # Fill Category dropdown
            try:
                category_dropdown = wait.until(EC.element_to_be_clickable(self.FORM_FIELDS['category']))
                select_category = Select(category_dropdown)
                try:
                    select_category.select_by_visible_text(category)
                    print(f"Selected category: {category}")
                except NoSuchElementException:
                    options = [opt.text.strip() for opt in select_category.options if opt.text.strip()]
                    if options:
                        select_category.select_by_visible_text(options[0])
                        print(f"Selected fallback category: {options[0]}")
                    else:
                        print("Warning: Category dropdown has no selectable options")
                # Wait for any page refresh/reload after category change
                time.sleep(0.5)
                # Re-check if we're still in the correct context (iframe/window)
                try:
                    driver.find_element(*self.FORM_FIELDS['date'])
                except NoSuchElementException:
                    # Lost context, try switching to iframe again
                    print("Lost form context after category selection, attempting to re-locate form...")
                    from automation_shared import go_to_swipe_form
                    driver.switch_to.default_content()
                    frames = driver.find_elements(By.TAG_NAME, "iframe")
                    for frame in frames:
                        try:
                            driver.switch_to.frame(frame)
                            if driver.find_elements(By.ID, "ctl00_BodyContentPlaceHolder_txtFromDate"):
                                print("Re-switched to swipe iframe")
                                break
                        except Exception:
                            driver.switch_to.default_content()
                    time.sleep(0.3)
            except Exception as e:
                print(f"Warning: Could not set category - {e}")

            # Fill Date field (wait for page reload completion)
            try:
                # Use JavaScript to set the date directly to avoid stale element issues
                date_selector = f"document.getElementById('{self.FORM_FIELDS['date'][1]}')"
                # Wait for element to exist in DOM
                wait.until(EC.presence_of_element_located(self.FORM_FIELDS['date']))
                time.sleep(0.2)  # Brief wait for page stability

                # Set date using pure JavaScript to avoid stale element reference
                js_script = f"""
                var dateField = {date_selector};
                if (dateField) {{
                    dateField.removeAttribute('readonly');
                    dateField.removeAttribute('disabled');
                    dateField.value = '{formatted_date}';
                    dateField.dispatchEvent(new Event('input', {{bubbles:true}}));
                    dateField.dispatchEvent(new Event('change', {{bubbles:true}}));
                    dateField.dispatchEvent(new Event('blur', {{bubbles:true}}));
                    return dateField.value;
                }}
                return null;
                """
                result_value = driver.execute_script(js_script)
                if result_value != formatted_date:
                    raise RuntimeError(f"Date field value did not persist. Got: {result_value}")
                print(f"Set date: {formatted_date}")
            except Exception as e:
                print(f"Error setting date: {e}")
                return {'success': False, 'message': f'Could not set date: {e}'}

            # Fill In/Out Type
            try:
                inout_dropdown = wait.until(EC.element_to_be_clickable(self.FORM_FIELDS['in_out_type']))
                select_inout = Select(inout_dropdown)

                if swipe_type.lower() == 'in':
                    select_inout.select_by_value('I')
                elif swipe_type.lower() == 'out':
                    select_inout.select_by_value('O')
                else:  # both
                    select_inout.select_by_value('B')

                print(f"Selected In/Out type: {swipe_type}")
            except Exception as e:
                print(f"Warning: Could not set In/Out type - {e}")

            # Fill In Time (if needed)
            if swipe_type.lower() in ['in', 'both']:
                try:
                    in_time_field = wait.until(EC.element_to_be_clickable(self.FORM_FIELDS['in_time']))
                    in_time_field.clear()
                    in_time_field.send_keys(in_time)
                    print(f"Set in time: {in_time}")
                except Exception as e:
                    print(f"Warning: Could not set in time - {e}")

            # Fill Out Time (if needed)
            if swipe_type.lower() in ['out', 'both']:
                try:
                    out_time_field = wait.until(EC.element_to_be_clickable(self.FORM_FIELDS['out_time']))
                    out_time_field.clear()
                    out_time_field.send_keys(out_time)
                    print(f"Set out time: {out_time}")
                except Exception as e:
                    print(f"Warning: Could not set out time - {e}")

            # Fill Reason
            try:
                reason_field = wait.until(EC.element_to_be_clickable(self.FORM_FIELDS['reason']))
                reason_field.clear()
                reason_field.send_keys(reason[:255])  # Limit to 255 characters
                print(f"Set reason: {reason[:50]}...")
            except Exception as e:
                print(f"Error setting reason: {e}")
                return {'success': False, 'message': f'Could not set reason: {e}'}

            # Submit the form
            try:
                save_button = wait.until(EC.element_to_be_clickable(self.FORM_FIELDS['save_button']))
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_button)
                time.sleep(0.1)
                try:
                    save_button.click()
                except ElementClickInterceptedException:
                    driver.execute_script("arguments[0].click();", save_button)
                print("Clicked save button")

                # Wait for response (reduced for faster execution)
                time.sleep(1)

                # Check for success or error messages
                return self.check_submission_result(driver, wait)

            except Exception as e:
                print(f"Error submitting form: {e}")
                return {'success': False, 'message': f'Could not submit form: {e}'}

        except Exception as e:
            logger.error(f"Error filling swipe form: {e}")
            return {'success': False, 'message': f'Form filling error: {e}'}

    def check_submission_result(self, driver, wait):
        """Check if the form submission was successful"""
        try:
            # Check for error messages
            try:
                error_elem = driver.find_element(*self.FORM_FIELDS['error_message'])
                error_text = error_elem.text.strip()
                if error_text:
                    print(f"Form error: {error_text}")
                    return {'success': False, 'message': error_text}
            except:
                pass

            # Check for success messages
            try:
                success_elem = driver.find_element(*self.FORM_FIELDS['success_message'])
                success_text = success_elem.text.strip()
                if success_text and 'success' in success_text.lower():
                    print(f"Form success: {success_text}")
                    return {'success': True, 'message': success_text}
            except:
                pass

            # Check if we're back to a list or confirmation page
            current_url = driver.current_url
            if 'AddSwipeRequest' not in current_url:
                print("Form submitted successfully - redirected to different page")
                return {'success': True, 'message': 'Swipe request submitted successfully'}

            # If form is still visible but no error, consider it successful
            print("Form submitted - no error messages detected")
            return {'success': True, 'message': 'Swipe request submitted (no error detected)'}

        except Exception as e:
            logger.error(f"Error checking submission result: {e}")
            return {'success': False, 'message': f'Could not verify submission: {e}'}

    def summarize_batch_results(self, results):
        """Summarize batch operation results"""
        total = len(results)
        successful = len([r for r in results if r['success']])
        failed = total - successful

        summary = {
            'total_requests': total,
            'successful': successful,
            'failed': failed,
            'success_rate': f"{(successful/total*100):.1f}%" if total > 0 else "0%",
            'results': results
        }

        if failed == 0:
            summary['overall_success'] = True
            summary['message'] = f"All {total} swipe requests submitted successfully!"
        else:
            summary['overall_success'] = False
            summary['message'] = f"{successful}/{total} swipe requests successful. {failed} failed."

        return summary

    def get_default_times_for_date(self, swipe_date):
        """Get intelligent default times based on date and patterns"""
        # This could be enhanced to learn from actual attendance patterns
        return self.DEFAULT_SHIFT['in_time'], self.DEFAULT_SHIFT['out_time']

    def validate_swipe_request(self, swipe_date, reason):
        """Validate swipe request parameters"""
        errors = []

        # Check date
        if not isinstance(swipe_date, date):
            errors.append("Invalid date format")
        elif swipe_date > date.today():
            errors.append("Cannot create swipe for future dates")
        elif swipe_date < date.today() - timedelta(days=90):
            errors.append("Cannot create swipe for dates older than 90 days")

        # Check reason
        if not reason or not reason.strip():
            errors.append("Reason cannot be empty")
        elif len(reason) > 255:
            errors.append("Reason too long (max 255 characters)")

        return errors

# Global instance
swipe_manager = SwipeRequestManager()

def submit_swipe_request(swipe_date, reason, in_time=None, out_time=None,
                        swipe_type='both', headless=None):
    """Quick function to submit a single swipe request"""
    return swipe_manager.submit_single_swipe(swipe_date, reason, in_time,
                                           out_time, swipe_type, headless=headless)

def submit_batch_swipe_requests(date_list, reason, in_time=None, out_time=None,
                               swipe_type='both', headless=None):
    """Quick function to submit batch swipe requests"""
    return swipe_manager.submit_batch_swipes(date_list, reason, in_time,
                                           out_time, swipe_type, headless=headless)


def get_recent_swipe_applications(limit=20, headless=None):
    """Quick function to retrieve recent swipe applications."""
    return swipe_manager.fetch_recent_swipe_applications(limit=limit, headless=headless)

if __name__ == "__main__":
    # Test the swipe manager
    print("Testing Swipe Manager...")

    # Test with yesterday's date
    test_date = date.today() - timedelta(days=1)
    result = submit_swipe_request(test_date, "Test swipe request")
    print("Test Result:", result)
