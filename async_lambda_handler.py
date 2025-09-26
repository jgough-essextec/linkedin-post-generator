"""
Dedicated Lambda handler for async image processing
This bypasses Zappa completely for image generation tasks
"""

import json
import logging
import os
import sys

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Dedicated handler for async image processing
    """
    try:
        logger.info(f"ASYNC LAMBDA: Starting with event: {event}")

        # Setup Django environment
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

        # Add current directory to path so Django can find our apps
        sys.path.insert(0, '/var/task')

        import django
        django.setup()

        # Import our async handler
        from async_handler import process_images_async

        # Process the images
        result = process_images_async(event, context)

        logger.info(f"ASYNC LAMBDA: Completed with result: {result}")
        return result

    except Exception as e:
        logger.error(f"ASYNC LAMBDA: Error processing images: {str(e)}")
        return {
            'statusCode': 500,
            'body': f'Error: {str(e)}'
        }