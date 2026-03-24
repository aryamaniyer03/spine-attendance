"""Flask API for Spine Clock-In/Clock-Out on Render"""

import os
import sys
from flask import Flask, jsonify, send_from_directory
from datetime import datetime

# Import automation modules
from automation import clock_in, clock_out

app = Flask(__name__)

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots")


def _format_notification(action, result):
    """Format a clean notification message for iOS Shortcuts.

    Returns (notification_title, notification_body, success).
    """
    success = result.get('success', False)
    message = result.get('message', 'Unknown error')

    if success:
        # e.g. "Clock-in verified - page shows: Clocked In at 3:35 PM, Today"
        # Extract just the time part for a clean notification
        if "at " in message:
            time_part = message.split("at ", 1)[1].rstrip(".")
            return f"✅ {action} Success", f"{action} at {time_part}", True
        return f"✅ {action} Success", message, True

    # Error cases - provide clear, actionable messages
    if "button failed" in message.lower():
        return f"❌ {action} Failed", f"Could not find the {action} button on the page. The HR portal layout may have changed.", False

    if "could not verify" in message.lower() or "check screenshots" in message.lower():
        return f"⚠️ {action} Unverified", f"Buttons were clicked but could not confirm it worked. Check /screenshots to see what happened.", False

    if "page shows" in message.lower() and not success:
        # Error indicator found on page
        error_detail = message.split("page shows: ", 1)[-1] if "page shows: " in message else message
        return f"❌ {action} Failed", f"HR portal error: {error_detail}", False

    if "login" in message.lower():
        return f"❌ {action} Failed", f"Could not log in to Spine HR. Password may have changed.", False

    if "attendance" in message.lower():
        return f"❌ {action} Failed", f"Logged in but could not find the attendance page.", False

    if "chrome" in message.lower() or "browser" in message.lower() or "driver" in message.lower():
        return f"❌ {action} Failed", f"Browser error: {message}", False

    if "timeout" in message.lower():
        return f"❌ {action} Failed", f"Page took too long to respond. Spine HR may be down.", False

    # Generic fallback
    return f"❌ {action} Failed", message, False


# Health check endpoint
@app.route('/')
def home():
    return jsonify({
        'status': 'running',
        'service': 'Spine Attendance Automation',
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            'clock_in': '/clock-in',
            'clock_out': '/clock-out',
            'health': '/health',
            'screenshots': '/screenshots',
        }
    })

@app.route('/health')
def health():
    """Health check for Render"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

def _run_with_retry(action_fn, action_name):
    """Run a clock action with one retry on crash."""
    last_error = None
    for attempt in range(2):
        try:
            result = action_fn(headless=True)
            if result.get('success'):
                title, body, success = _format_notification(action_name, result)
                return jsonify({
                    'success': success,
                    'title': title,
                    'body': body,
                    'notification': f"{title}\n{body}",
                    'detail': result.get('message', ''),
                    'screenshot': result.get('screenshot'),
                    'attempt': attempt + 1,
                    'timestamp': datetime.now().isoformat()
                }), 200

            # Not successful but no crash — return the error
            title, body, success = _format_notification(action_name, result)
            return jsonify({
                'success': success,
                'title': title,
                'body': body,
                'notification': f"{title}\n{body}",
                'detail': result.get('message', ''),
                'screenshot': result.get('screenshot'),
                'attempt': attempt + 1,
                'timestamp': datetime.now().isoformat()
            }), 422

        except Exception as e:
            last_error = e
            error_first_line = str(e).split('\n')[0][:200]
            print(f"[{action_name}] Attempt {attempt + 1} crashed: {error_first_line}")
            if attempt == 0:
                print(f"[{action_name}] Retrying...")
                import gc; gc.collect()  # Free memory before retry
                continue

    # Both attempts failed
    error_msg = str(last_error).split('\n')[0][:200]
    return jsonify({
        'success': False,
        'title': f'❌ {action_name} Failed',
        'body': f'Chrome crashed on both attempts: {error_msg}',
        'notification': f'❌ {action_name} Failed\nChrome crashed on both attempts: {error_msg}',
        'detail': str(last_error),
        'attempt': 2,
        'timestamp': datetime.now().isoformat()
    }), 500


@app.route('/clock-in')
def trigger_clock_in():
    """Trigger clock-in automation"""
    return _run_with_retry(clock_in, "Clock-In")

@app.route('/clock-out')
def trigger_clock_out():
    """Trigger clock-out automation"""
    return _run_with_retry(clock_out, "Clock-Out")

@app.route('/screenshots')
def list_screenshots():
    """List all saved screenshots for debugging."""
    if not os.path.exists(SCREENSHOTS_DIR):
        return jsonify({'screenshots': [], 'message': 'No screenshots directory yet.'})

    files = sorted(os.listdir(SCREENSHOTS_DIR), reverse=True)
    screenshots = [f for f in files if f.endswith('.png')]
    return jsonify({
        'screenshots': screenshots,
        'count': len(screenshots),
        'view_url': '/screenshots/<filename>',
    })

@app.route('/screenshots/<filename>')
def view_screenshot(filename):
    """View a specific screenshot."""
    return send_from_directory(SCREENSHOTS_DIR, filename)

@app.route('/screenshots/cleanup')
def cleanup_screenshots():
    """Delete all screenshots older than 7 days."""
    if not os.path.exists(SCREENSHOTS_DIR):
        return jsonify({'deleted': 0})

    import time as _time
    cutoff = _time.time() - (7 * 24 * 3600)
    deleted = 0
    for f in os.listdir(SCREENSHOTS_DIR):
        path = os.path.join(SCREENSHOTS_DIR, f)
        if os.path.getmtime(path) < cutoff:
            os.remove(path)
            deleted += 1

    return jsonify({'deleted': deleted})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
