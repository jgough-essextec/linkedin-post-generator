"""
Custom Lambda handler that can handle both Django requests and async image processing
"""

import json
import logging
import os

# Setup logging
logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    """
    Main Lambda handler that routes to appropriate processing
    """
    logger.info(f"Lambda handler called with event keys: {list(event.keys()) if isinstance(event, dict) else 'not dict'}")

    # Check if this is an async image processing request
    # The event structure for direct Lambda invoke is different than API Gateway
    if isinstance(event, dict) and event.get('action') == 'process_images':
        # This is an async image processing request
        logger.info(f"MAIN HANDLER: Detected async image processing request: {event}")

        # Setup Django for async processing
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        import django
        django.setup()

        from async_handler import process_images_async
        return process_images_async(event, context)

    # Otherwise, handle as a normal Django web request using Zappa's default handler
    logger.info("Handling as Django web request")

    # Import and use the standard Django WSGI application through Zappa
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    import django
    django.setup()

    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()

    # Use Zappa to handle the WSGI request
    from zappa.wsgi import create_wsgi_request
    environ = create_wsgi_request(event, script_name='', base64_content_types=set(), text_content_types=set())

    from io import StringIO
    from django.http import HttpResponse

    def start_response(status, headers, exc_info=None):
        pass

    response_data = application(environ, start_response)

    # Convert WSGI response to Lambda format
    status_code = 200
    body = b''.join(response_data).decode('utf-8')

    return {
        'statusCode': status_code,
        'body': body,
        'headers': {
            'Content-Type': 'text/html'
        }
    }