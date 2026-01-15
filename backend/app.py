# Headless Music Player - Main Application
import os
import sys
import logging
import threading
import time

# Set up logging before other imports
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d | %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Suppress pygame welcome message
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from flask import Flask, send_from_directory, render_template
from flask_cors import CORS

from models.state import load_state, save_state
from services import player, library
from routes.api import api


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    CORS(app)
    
    # Register blueprints
    app.register_blueprint(api)
    
    # Static file serving
    @app.route('/')
    @app.route('/index.html')
    def index():
        return render_template('index.html')
    
    @app.route('/assets/<path:path>')
    def serve_assets(path):
        # Vite builds to assets/assets/, so we serve from there
        return send_from_directory('assets/assets', path)
    
    return app


def background_tasks():
    """Background thread for periodic tasks."""
    while True:
        try:
            # Check if track ended
            player.check_track_ended()
            
            # Periodic state save
            save_state()
            
        except Exception as e:
            logger.error(f"Background task error: {e}")
        
        time.sleep(1)


def init_application():
    """Initialize the application (player, library, state)."""
    logger.info("=" * 50)
    logger.info("Headless Music Player Starting")
    logger.info("=" * 50)
    
    # Load saved state
    load_state()
    
    # Initialize player
    player.init_player()
    
    # Scan music library
    library.scan_library()
    
    # Restore playback state
    player.restore_state()
    
    # Start background thread
    bg_thread = threading.Thread(target=background_tasks, daemon=True)
    bg_thread.start()
    
    logger.info("Application initialized")


# Initialize and create app at module level for gunicorn
init_application()
app = create_app()


def main():
    """Main entry point for development."""
    logger.info("Server starting on http://0.0.0.0:8000")
    app.run(host='0.0.0.0', port=8000, debug=False, threaded=True)


if __name__ == '__main__':
    main()

