#!/usr/bin/env python3
"""
upload_log.py - Upload ArduPilot flight logs to Firebase Storage

This script finds the most recent ArduPilot .bin flight log file from a specified directory
and uploads it to Firebase Storage at path: /logs/{taskId}.bin.
"""
import argparse
import os
import glob
import logging
from datetime import datetime
from typing import Optional, Tuple

import firebase_admin
from firebase_admin import credentials, storage
from dotenv import load_dotenv


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("upload_log")


def find_pixhawk_mount_paths() -> list:
    """
    Attempt to find Pixhawk mount points on the system.
    
    Returns:
        List of potential Pixhawk mounted log directories
    """
    potential_paths = []
    
    # Common base mount points
    mount_base_dirs = [
        "/media/pi",       # Common for Raspberry Pi
        "/media/$USER",    # Some Linux distros
        "/mnt",            # Alternative mount location
        "/run/media/$USER" # For some Linux distributions
    ]
    
    # Replace $USER with actual username if needed
    username = os.environ.get("USER", "pi")
    mount_base_dirs = [path.replace("$USER", username) for path in mount_base_dirs]
    
    # Common Pixhawk volume names
    pixhawk_names = ["PIXHAWK", "APM", "PX4", "FMUV", "MINDPX"]
    
    # Check for mounted Pixhawk
    for base_dir in mount_base_dirs:
        if os.path.exists(base_dir):
            # Look for directories that might be a Pixhawk
            for item in os.listdir(base_dir):
                full_path = os.path.join(base_dir, item)
                if os.path.isdir(full_path):
                    # Check if directory name matches known Pixhawk names
                    if any(pixname in item.upper() for pixname in pixhawk_names):
                        # Add the APM/logs directory if it exists
                        logs_path = os.path.join(full_path, "APM", "logs")
                        if os.path.isdir(logs_path):
                            potential_paths.append(logs_path)
                        # Also check for logs directly in the root
                        logs_path = os.path.join(full_path, "logs")
                        if os.path.isdir(logs_path):
                            potential_paths.append(logs_path)
    
    logger.info(f"Found {len(potential_paths)} potential Pixhawk log directories: {potential_paths}")
    return potential_paths


def find_latest_bin_file(logs_dir: str) -> Optional[str]:
    """
    Find the most recent .bin file in the specified directory or in Pixhawk mount paths.
    
    Args:
        logs_dir: Path to the directory containing log files
        
    Returns:
        Path to the latest .bin file or None if not found
    """
    # List to store all found bin files
    all_bin_files = []
    
    # First, check the specified logs directory
    if os.path.isdir(logs_dir):
        bin_files = glob.glob(os.path.join(logs_dir, "*.bin"))
        for file in bin_files:
            all_bin_files.append(file)
        logger.info(f"Found {len(bin_files)} .bin files in specified logs directory: {logs_dir}")
    else:
        logger.warning(f"Specified log directory does not exist: {logs_dir}")
    
    # Next, try to find auto-mounted Pixhawk devices
    pixhawk_paths = find_pixhawk_mount_paths()
    for path in pixhawk_paths:
        bin_files = glob.glob(os.path.join(path, "*.bin"))
        for file in bin_files:
            all_bin_files.append(file)
        logger.info(f"Found {len(bin_files)} .bin files in auto-discovered path: {path}")
    
    if not all_bin_files:
        logger.warning("No .bin files found in any location")
        return None
    
    # Sort files by modification time (newest first)
    latest_file = max(all_bin_files, key=os.path.getmtime)
    logger.info(f"Found latest log file: {latest_file} (modified: {datetime.fromtimestamp(os.path.getmtime(latest_file))})")
    
    return latest_file


def initialize_firebase(credentials_path: str, bucket_name: str) -> Optional[firebase_admin.App]:
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
        logger.info("Firebase initialized successfully")
        return app
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {str(e)}")
        return None


def upload_to_firebase(file_path: str, destination_path: str) -> bool:
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
        
        logger.info(f"Successfully uploaded {file_path} to {destination_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to upload file: {str(e)}")
        return False


def load_config() -> Tuple[str, str, str, str]:
    """
    Load configuration from environment variables.
    
    Returns:
        Tuple of (credentials_path, storage_bucket, logs_dir, task_id)
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Get required environment variables
    credentials_path = os.environ.get("CREDENTIALS_PATH")
    storage_bucket = os.environ.get("STORAGE_BUCKET")
    logs_dir = os.environ.get("LOGS_DIR")
    task_id = os.environ.get("TASK_ID")
    
    # Validate required environment variables
    if not credentials_path:
        logger.error("CREDENTIALS_PATH environment variable is not set")
    if not storage_bucket:
        logger.error("STORAGE_BUCKET environment variable is not set")
    if not logs_dir:
        logger.error("LOGS_DIR environment variable is not set")
    if not task_id:
        logger.error("TASK_ID environment variable is not set")
    
    return credentials_path, storage_bucket, logs_dir, task_id


def main():
    """Main entry point for the script."""
    # Load configuration
    credentials_path, storage_bucket, logs_dir, task_id = load_config()
    
    # Validate configuration
    if not all([credentials_path, storage_bucket, logs_dir, task_id]):
        logger.error("Missing required configuration. Please check your .env file.")
        return 1
    
    # Find the latest log file
    latest_log = find_latest_bin_file(logs_dir)
    if not latest_log:
        logger.error("No log file found to upload")
        return 1
    
    # Initialize Firebase
    app = initialize_firebase(credentials_path, storage_bucket)
    if not app:
        logger.error("Failed to initialize Firebase")
        return 1
    
    # Upload the log file
    destination_path = f"logs/{task_id}.bin"
    success = upload_to_firebase(latest_log, destination_path)
    
    # Clean up Firebase resources
    firebase_admin.delete_app(app)
    
    if success:
        logger.info(f"Upload completed successfully to {destination_path}")
        return 0
    else:
        logger.error("Upload failed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
