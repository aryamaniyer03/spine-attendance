"""Flask API for Spine Clock-In/Clock-Out on Render"""

import os
import sys
from flask import Flask, jsonify, send_from_directory
from datetime import datetime

# Import automation modules
from automation import clock_in, clock_out

app = Flask(__name__)

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots")

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

@app.route('/clock-in')
def trigger_clock_in():
    """Trigger clock-in automation"""
    try:
        result = clock_in(headless=True)
        status_code = 200 if result.get('success', False) else 422
        return jsonify({
            'success': result.get('success', False),
            'message': result.get('message', 'Unknown error'),
            'screenshot': result.get('screenshot'),
            'timestamp': datetime.now().isoformat()
        }), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error during clock-in: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/clock-out')
def trigger_clock_out():
    """Trigger clock-out automation"""
    try:
        result = clock_out(headless=True)
        status_code = 200 if result.get('success', False) else 422
        return jsonify({
            'success': result.get('success', False),
            'message': result.get('message', 'Unknown error'),
            'screenshot': result.get('screenshot'),
            'timestamp': datetime.now().isoformat()
        }), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error during clock-out: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

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
