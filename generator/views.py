from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.http import require_http_methods
import logging
import json
import boto3

from .models import GeneratedPost
from .services.scraper import scrape_content
from .services.ai_generator import AIGenerator
from .services.storage import S3StorageService

logger = logging.getLogger(__name__)


def trigger_async_image_generation(post_id, summary_text):
    """
    Trigger async image generation using Lambda invoke
    """
    try:
        lambda_client = boto3.client('lambda', region_name='us-east-1')

        payload = {
            'post_id': post_id,
            'summary_text': summary_text
        }

        # Invoke async image processing (dedicated async Lambda)
        response = lambda_client.invoke(
            FunctionName='linkedin-generator-async-dev',
            InvocationType='Event',  # Async invocation
            Payload=json.dumps(payload)  # No need for 'action' field anymore
        )

        logger.info(f"Triggered async image generation for post {post_id}, response: {response.get('StatusCode')}")

    except Exception as e:
        logger.error(f"Failed to trigger async image generation: {str(e)}")
        raise


def index_view(request):
    """
    Main page for submitting a URL
    """
    # Default prompt for the user to modify
    default_prompt = """Please create a professional LinkedIn post that:
- Highlights key insights from the article
- Includes actionable takeaways for business professionals
- Uses an engaging tone that encourages discussion
- Contains relevant hashtags for maximum reach
"""

    context = {
        'default_prompt': default_prompt
    }
    return render(request, 'generator/index.html', context)


@csrf_protect
@require_http_methods(["POST"])
def generate_view(request):
    """
    Handle POST request to generate LinkedIn content
    """
    try:
        # Get form data
        source_url = request.POST.get('source_url', '').strip()
        user_prompt_adjustment = request.POST.get('user_prompt_adjustment', '').strip()

        if not source_url:
            messages.error(request, 'Please provide a valid URL')
            return redirect('generator:index')

        # Step 1: Scrape content
        scrape_result = scrape_content(source_url)
        if not scrape_result['success']:
            messages.error(request, f"Failed to scrape content: {scrape_result['error']}")
            return redirect('generator:index')

        scraped_content = scrape_result['content']

        # Step 2: Generate AI content
        ai_generator = AIGenerator()
        ai_result = ai_generator.generate_text_content(scraped_content, user_prompt_adjustment)

        if not ai_result['success']:
            messages.error(request, f"Failed to generate content: {ai_result['error']}")
            return redirect('generator:index')

        generated_data = ai_result['data']

        # Step 3: Skip sync image generation to stay under 29-second API Gateway timeout
        image_urls = [None, None]

        # Step 5: Create markdown content
        markdown_content = ai_generator.create_markdown_content(
            generated_data,
            [url for url in image_urls if url]
        )

        # Step 6: Save to database with async image processing enabled
        generated_post = GeneratedPost.objects.create(
            source_url=source_url,
            original_content=scraped_content,
            user_prompt_adjustment=user_prompt_adjustment,
            linkedin_post=generated_data['linkedin_post'],
            summary=generated_data['summary'],
            business_rationale=generated_data['business_rationale'],
            image_url_1=image_urls[0],
            image_url_2=image_urls[1],
            markdown_content=markdown_content,
            images_processing=True  # Enable async image processing
        )

        # Step 7: Trigger async image generation
        try:
            logger.info(f"About to trigger async image generation for post {generated_post.id}")
            trigger_async_image_generation(generated_post.id, generated_data['summary'])
            logger.info(f"Successfully triggered async image generation for post {generated_post.id}")
        except Exception as e:
            logger.error(f"Failed to trigger async image generation: {str(e)}")
            # If async trigger fails, set processing to false so user doesn't wait indefinitely
            generated_post.images_processing = False
            generated_post.save()
            # Re-raise to see the error in logs
            raise

        messages.success(request, 'LinkedIn post generated successfully!')
        return redirect('generator:result', post_id=generated_post.id)

    except Exception as e:
        logger.error(f"Error in generate_view: {str(e)}")
        messages.error(request, 'An unexpected error occurred. Please try again.')
        return redirect('generator:index')


def result_view(request, post_id):
    """
    Display the generated content
    """
    generated_post = get_object_or_404(GeneratedPost, id=post_id)

    context = {
        'post': generated_post
    }
    return render(request, 'generator/result.html', context)


def download_markdown_view(request, post_id):
    """
    Download the markdown content as a file
    """
    generated_post = get_object_or_404(GeneratedPost, id=post_id)

    # Create HTTP response with markdown content
    response = HttpResponse(
        generated_post.markdown_content,
        content_type='text/markdown'
    )

    # Set filename for download
    filename = f"linkedin_post_{generated_post.id}_{generated_post.created_at.strftime('%Y%m%d_%H%M')}.md"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


@require_http_methods(["GET"])
def check_image_status(request, post_id):
    """
    API endpoint to check if image processing is complete
    """
    try:
        post = get_object_or_404(GeneratedPost, id=post_id)

        return JsonResponse({
            'images_processing': post.images_processing,
            'images_completed': not post.images_processing,
            'image_url_1': post.image_url_1,
            'image_url_2': post.image_url_2,
            'images_completed_at': post.images_completed_at.isoformat() if post.images_completed_at else None
        })

    except Exception as e:
        logger.error(f"Error checking image status: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# API endpoint for checking generation status (optional)
def history_view(request):
    """
    Display all previously generated posts in a table
    """
    posts = GeneratedPost.objects.all().order_by('-created_at')

    context = {
        'posts': posts
    }
    return render(request, 'generator/history.html', context)


@csrf_exempt
def test_async_view(request):
    """
    Test endpoint to debug async image generation
    """
    if request.method == 'POST':
        try:
            # Create a test post
            test_post = GeneratedPost.objects.create(
                source_url="https://test.com",
                original_content="Test content",
                user_prompt_adjustment="",
                linkedin_post="Test LinkedIn post",
                summary="Test summary for image generation",
                business_rationale="Test rationale",
                images_processing=True
            )

            logger.info(f"TEST: Created test post {test_post.id}")

            # Try to trigger async image generation
            try:
                trigger_async_image_generation(test_post.id, test_post.summary)
                logger.info(f"TEST: Successfully triggered async for post {test_post.id}")
                return JsonResponse({
                    'success': True,
                    'post_id': test_post.id,
                    'message': 'Async generation triggered'
                })
            except Exception as e:
                logger.error(f"TEST: Failed to trigger async: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': f'Async trigger failed: {str(e)}'
                })

        except Exception as e:
            logger.error(f"TEST: Error creating test post: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Test setup failed: {str(e)}'
            })

    # GET request - show test form
    return JsonResponse({
        'message': 'POST to this endpoint to test async image generation',
        'recent_posts': list(GeneratedPost.objects.filter(images_processing=True).values('id', 'created_at', 'images_processing')[:5])
    })


def status_view(request, post_id):
    """
    API endpoint to check generation status (for future async implementation)
    """
    try:
        generated_post = get_object_or_404(GeneratedPost, id=post_id)

        return JsonResponse({
            'status': 'completed',
            'post_id': generated_post.id,
            'created_at': generated_post.created_at.isoformat()
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)
