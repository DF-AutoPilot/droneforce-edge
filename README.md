# DroneForce Log Uploader

A Python utility for automatically uploading ArduPilot flight logs to Firebase Storage. This tool is designed to run on a Raspberry Pi as part of the DroneForce Protocol workflow after drone flights.

## Features

- Automatically finds the most recent `.bin` flight log file
- Uploads the log to Firebase Storage with organized path structure
- Configurable via environment variables or `.env` file
- Command-line interface for easy integration with automated workflows

## Requirements

- Python 3.x
- `firebase-admin` package
- `python-dotenv` package

## Installation

1. Clone this repository to your Raspberry Pi

2. Install the required dependencies:
   ```
   pip install firebase-admin python-dotenv
   ```

3. Create a `.env` file with the following variables:
   ```
   CREDENTIALS_PATH=/path/to/your/firebase-credentials.json
   STORAGE_BUCKET=your-firebase-bucket-name.appspot.com
   LOGS_DIR=/path/to/ardupilot/logs
   TASK_ID=your-unique-task-identifier
   ```

## Usage

Run the script to upload the latest log file:

```
python upload_log.py
```

The log will be uploaded to Firebase Storage at the path `/logs/{TASK_ID}.bin` where `{TASK_ID}` is the value from your `.env` file.

## Integration

This script can be:

- Run manually after flights
- Integrated with a post-flight hook
- Scheduled via cron job
- Triggered by other DroneForce Protocol components

## Example Cron Job

To run the uploader automatically every hour:

```
0 * * * * cd /path/to/script && python upload_log.py >> /var/log/droneforce/upload.log 2>&1
```

If you want to use dynamic task IDs with timestamps, you can create a wrapper script that sets the TASK_ID environment variable before running the main script:

```bash
#!/bin/bash
export TASK_ID="flight_$(date +%Y%m%d%H%M)" 
python upload_log.py
```

## Troubleshooting

- Ensure the Firebase credentials JSON file has proper permissions
- Check that the log directory exists and contains `.bin` files
- Verify that the Raspberry Pi has internet connectivity
- Review the script output for detailed error messages
