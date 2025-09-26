"""
Async Image Processing Lambda Function
Handles image generation in the background to avoid API Gateway timeouts
"""

import json
import logging
import os
import sys
import django
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.append('/opt')
django.setup()

from generator.models import GeneratedPost
from generator.services.ai_generator import AIGenerator
from generator.services.storage import S3StorageService

logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    """
    Lambda handler for async image processing

    Expected event format:
    {
        "post_id": 123,
        "summary_text": "Generated summary for image prompts"
    }
    """
    try:
        logger.info(f"Starting async image processing: {event}")

        # Extract parameters
        post_id = event.get('post_id')
        summary_text = event.get('summary_text', '')

        if not post_id:
            raise ValueError("post_id is required")

        # Get the post from database
        try:
            post = GeneratedPost.objects.get(id=post_id)
        except GeneratedPost.DoesNotExist:
            raise ValueError(f"Post with id {post_id} not found")

        # Check if already processed
        if not post.images_processing:
            logger.info(f"Post {post_id} images already processed")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Images already processed'})
            }

        # Generate images
        logger.info(f"Generating images for post {post_id}")
        ai_generator = AIGenerator()
        image_result = ai_generator.generate_images(summary_text)

        image_urls = [None, None]

        if image_result['success'] and image_result['images']:
            # Upload images to S3
            logger.info(f"Uploading {len(image_result['images'])} images to S3")
            storage_service = S3StorageService()

            for i, image_data in enumerate(image_result['images'][:2]):
                try:
                    upload_result = storage_service.upload_image(
                        image_data,
                        f"linkedin_post_{post_id}"
                    )
                    if upload_result['success']:
                        image_urls[i] = upload_result['url']
                        logger.info(f"Image {i+1} uploaded: {upload_result['url']}")
                    else:
                        logger.error(f"Failed to upload image {i+1}: {upload_result['error']}")
                except Exception as e:
                    logger.error(f"Error uploading image {i+1}: {str(e)}")

        else:
            logger.warning(f"Image generation failed: {image_result.get('error', 'Unknown error')}")

        # Update post in database
        post.image_url_1 = image_urls[0]
        post.image_url_2 = image_urls[1]
        post.images_processing = False
        post.images_completed_at = timezone.now()

        # Update markdown content with new image URLs
        if any(image_urls):
            post.markdown_content = ai_generator.create_markdown_content(
                {
                    'linkedin_post': post.linkedin_post,
                    'summary': post.summary,
                    'business_rationale': post.business_rationale
                },
                [url for url in image_urls if url]
            )

        post.save()

        logger.info(f"Successfully processed images for post {post_id}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Image processing completed',
                'post_id': post_id,
                'images_generated': len([url for url in image_urls if url])
            })
        }

    except Exception as e:
        logger.error(f"Error in async image processing: {str(e)}")

        # Mark processing as failed if we have a post_id
        if 'post_id' in locals():
            try:
                post = GeneratedPost.objects.get(id=post_id)
                post.images_processing = False
                post.save()
            except:
                pass

        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Image processing failed'
            })
        }


if __name__ == '__main__':
    # Test locally
    test_event = {
        'post_id': 1,
        'summary_text': 'Test summary for image generation'
    }
    result = lambda_handler(test_event, {})
    print(json.dumps(result, indent=2))