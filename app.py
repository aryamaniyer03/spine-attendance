"""Flask API for Spine Clock-In/Clock-Out on Render"""

import os
import sys
from flask import Flask, jsonify
from datetime import datetime

# Import automation modules
from automation import clock_in, clock_out

app = Flask(__name__)

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
            'health': '/health'
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
        return jsonify({
            'success': result.get('success', False),
            'message': result.get('message', 'Unknown error'),
            'timestamp': datetime.now().isoformat()
        })
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
        return jsonify({
            'success': result.get('success', False),
            'message': result.get('message', 'Unknown error'),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error during clock-out: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
