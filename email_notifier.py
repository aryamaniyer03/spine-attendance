"""Simple email notifier stub."""

def send_email_with_screenshot(action, success, screenshot_path, error_message=None):
    """Stub function for email notifications - does nothing for now."""
    print(f"[EMAIL STUB] Would send email: {action} {'succeeded' if success else 'failed'}")
    if error_message:
        print(f"[EMAIL STUB] Error: {error_message}")
    print(f"[EMAIL STUB] Screenshot: {screenshot_path}")
