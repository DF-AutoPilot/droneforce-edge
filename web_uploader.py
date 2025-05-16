#!/usr/bin/env python3
"""
web_uploader.py - Web UI for uploading ArduPilot flight logs to Firebase Storage

This script provides a simple web interface to select and upload log files to Firebase Storage.
It's designed to run on a headless server and be accessed via a web browser.
"""
import os
import logging
from flask import Flask, request, render_template, flash, redirect, url_for
import firebase_admin
from firebase_admin import credentials, storage
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import tempfile
import shutil

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("web_uploader")

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB max upload size

# Global variable for Firebase app
firebase_app = None

def initialize_firebase(credentials_path, bucket_name):
    """
    Initialize Firebase Admin SDK with the given credentials.
    
    Args:
        credentials_path: Path to the credentials JSON file
        bucket_name: Name of the Storage bucket
        
    Returns:
        Firebase app instance or None if initialization failed
    """
    try:
        cred = credentials.Certificate(credentials_path)
        app = firebase_admin.initialize_app(cred, {
            'storageBucket': bucket_name
        })
        logger.info(f"Firebase initialized successfully with bucket: {bucket_name}")
        return app
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {str(e)}")
        return None

def upload_to_firebase(file_path, destination_path):
    """
    Upload a file to Firebase Storage.
    
    Args:
        file_path: Path to the local file to upload
        destination_path: Destination path in Firebase Storage
        
    Returns:
        True if upload was successful, False otherwise
    """
    try:
        bucket = storage.bucket()
        blob = bucket.blob(destination_path)
        
        # Upload the file
        blob.upload_from_filename(file_path)
        logger.info(f"File uploaded to {destination_path}")
        
        # Make the file publicly accessible
        blob.make_public()
        logger.info(f"Download URL: {blob.public_url}")
        
        return True, blob.public_url
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return False, None

def load_config():
    """
    Load configuration from environment variables.
    
    Returns:
        Tuple of (credentials_path, storage_bucket)
    """
    load_dotenv()
    
    credentials_path = os.environ.get("CREDENTIALS_PATH")
    storage_bucket = os.environ.get("STORAGE_BUCKET")
    
    if not credentials_path:
        logger.error("CREDENTIALS_PATH environment variable not set.")
        return None, None
    
    if not os.path.isfile(credentials_path):
        logger.error(f"Credentials file not found at: {credentials_path}")
        return None, None
    
    if not storage_bucket:
        logger.error("STORAGE_BUCKET environment variable not set.")
        return None, None
    
    return credentials_path, storage_bucket

@app.route('/')
def index():
    """Home page with upload form"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle log file upload"""
    if 'logfile' not in request.files:
        flash('No file selected')
        return redirect(request.url)
    
    file = request.files['logfile']
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
    
    task_id = request.form.get('task_id', 'undefined_task')
    
    # Create a temporary file to store the uploaded content
    temp_dir = tempfile.mkdtemp()
    try:
        temp_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(temp_path)
        
        # Upload to Firebase
        destination_path = f"logs/{task_id}_{os.path.basename(secure_filename(file.filename))}"
        success, url = upload_to_firebase(temp_path, destination_path)
        
        if success:
            flash(f'File uploaded successfully to {destination_path}')
            if url:
                flash(f'Download URL: {url}')
            return render_template('success.html', filename=file.filename, task_id=task_id, url=url)
        else:
            flash('Upload failed. Please check logs for details.')
            return redirect('/')
    
    finally:
        # Clean up temp directory
        shutil.rmtree(temp_dir)

@app.route('/health')
def health():
    """Health check endpoint"""
    return {"status": "up", "firebase": "initialized" if firebase_app else "not initialized"}

def main():
    """Main entry point for the application"""
    # Load configuration
    credentials_path, storage_bucket = load_config()
    if not credentials_path or not storage_bucket:
        logger.error("Failed to load required configuration. Check your .env file.")
        return 1
    
    # Initialize Firebase
    global firebase_app
    firebase_app = initialize_firebase(credentials_path, storage_bucket)
    if not firebase_app:
        logger.error("Failed to initialize Firebase.")
        return 1
    
    # Run the Flask app
    logger.info("Starting web server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)
    return 0

if __name__ == "__main__":
    exit(main())
