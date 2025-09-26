"""
Async image processing handler for the main Lambda function
"""

import json
import logging
import os
from django.utils import timezone
from generator.models import GeneratedPost
from generator.services.ai_generator import AIGenerator
from generator.services.storage import S3StorageService

logger = logging.getLogger(__name__)


def process_images_async(event, context):
    """
    Handle async image processing within the main Lambda
    """
    try:
        logger.info(f"ASYNC HANDLER: Starting image processing with event: {event}")

        # Extract parameters
        post_id = event.get('post_id')
        summary_text = event.get('summary_text', '')

        logger.info(f"ASYNC HANDLER: Extracted post_id={post_id}, summary_length={len(summary_text)}")

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
            return {'statusCode': 200, 'body': 'Images already processed'}

        # Generate images
        logger.info(f"Generating images for post {post_id}")
        ai_generator = AIGenerator()
        image_result = ai_generator.generate_images(summary_text)

        image_urls = [None, None]
        image_prompts = [None, None]

        # Extract prompts from the result
        if 'prompts' in image_result and image_result['prompts']:
            image_prompts = image_result['prompts'][:2]  # Take first 2 prompts
            logger.info(f"Generated prompts: {image_prompts}")

        if image_result['success'] and image_result['images']:
            # Upload images to S3
            logger.info(f"Uploading {len(image_result['images'])} images to S3")
            storage_service = S3StorageService()

            for i, image_data in enumerate(image_result['images'][:2]):
                if image_data is not None:  # Only process non-None images
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

        # Update post in database
        post.image_url_1 = image_urls[0]
        post.image_url_2 = image_urls[1]
        post.image_prompt_1 = image_prompts[0] if len(image_prompts) > 0 else None
        post.image_prompt_2 = image_prompts[1] if len(image_prompts) > 1 else None
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
            'body': f'Processed {len([url for url in image_urls if url])} images'
        }

    except Exception as e:
        logger.error(f"Error in async image processing: {str(e)}")

        # Mark processing as failed if we have a post_id
        if 'post_id' in locals() and post_id:
            try:
                post = GeneratedPost.objects.get(id=post_id)
                post.images_processing = False
                post.save()
            except:
                pass

        return {'statusCode': 500, 'body': f'Error: {str(e)}'}