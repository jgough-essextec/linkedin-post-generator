import boto3
import json
import base64
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class AIGenerator:
    """Service for generating LinkedIn posts and images using AWS Bedrock"""

    def __init__(self):
        import os

        # For Lambda, use default credential chain (no explicit credentials)
        # Set region explicitly
        region = 'us-east-1'

        # Create session first, then client
        session = boto3.Session(region_name=region)
        self.bedrock_client = session.client('bedrock-runtime')

        # Log for debugging
        logger.info(f"Bedrock client created with region: {region}")

        try:
            # Test credentials - bedrock-runtime doesn't have list_foundation_models
            # Just log that client was created successfully
            logger.info("Bedrock runtime client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to create Bedrock client: {str(e)}")

        # Model configurations - using models that support on-demand throughput
        self.text_model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"  # This version supports on-demand
        # Note: Nova Canvas might not be available - using Titan as fallback
        self.image_model_nova = "amazon.titan-image-generator-v2:0"  # Using Titan for both for now
        self.image_model_titan = "amazon.titan-image-generator-v2:0"  # Titan G1 v2 for image 2

    def generate_text_content(self, scraped_content, user_prompt_adjustment=""):
        """
        Generate LinkedIn post, summary, and business rationale using Claude

        Args:
            scraped_content (str): The scraped article content
            user_prompt_adjustment (str): Additional user instructions

        Returns:
            dict: Generated content with 'success', 'data', and 'error' keys
        """
        try:
            # Construct the prompt
            base_prompt = f"""
            Based on the following article content, create a professional LinkedIn post with business insights.

            Article Content:
            {scraped_content}

            {f"Additional Instructions: {user_prompt_adjustment}" if user_prompt_adjustment else ""}

            Please respond with a JSON object containing exactly these fields:
            {{
                "linkedin_post": "A professional LinkedIn post (2-3 paragraphs, engaging, with relevant hashtags)",
                "summary": "A concise summary of the key points from the article (3-4 sentences)",
                "business_rationale": "Explanation of why this content is valuable for business professionals (2-3 sentences)"
            }}

            Make sure the LinkedIn post is:
            - Professional yet engaging
            - Includes relevant insights and takeaways
            - Contains 3-5 relevant hashtags
            - Is optimized for LinkedIn engagement
            - Between 150-300 words

            Return only valid JSON.
            """

            # Prepare the request
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "messages": [
                    {
                        "role": "user",
                        "content": base_prompt
                    }
                ],
                "temperature": 0.7
            }

            # Make the API call
            response = self.bedrock_client.invoke_model(
                modelId=self.text_model_id,
                body=json.dumps(request_body)
            )

            # Parse response
            response_body = json.loads(response['body'].read())
            generated_text = response_body['content'][0]['text']

            # Try to parse the JSON response
            try:
                generated_content = json.loads(generated_text)

                # Validate required fields
                required_fields = ['linkedin_post', 'summary', 'business_rationale']
                if not all(field in generated_content for field in required_fields):
                    raise ValueError("Missing required fields in generated content")

                return {
                    'success': True,
                    'data': generated_content,
                    'error': None
                }

            except json.JSONDecodeError:
                # Fallback: try to extract content even if not proper JSON
                logger.warning("Generated content is not valid JSON, attempting fallback parsing")
                return {
                    'success': False,
                    'data': None,
                    'error': 'Generated content is not in valid JSON format'
                }

        except Exception as e:
            logger.error(f"Error generating text content: {str(e)}")
            return {
                'success': False,
                'data': None,
                'error': f'Failed to generate content: {str(e)}'
            }

    def _create_context_aware_prompts(self, text_content):
        """
        Create dynamic image prompts based on article content using AI analysis

        Args:
            text_content (str): The article summary or content to analyze

        Returns:
            list: Two context-aware image prompts
        """
        try:
            # Use Claude to analyze content and generate appropriate image prompts
            prompt_generation_request = f"""
            Based on this article content: "{text_content}"

            Create 2 distinct, professional image prompts for LinkedIn posts. Each prompt should:
            1. Be relevant to the article's main theme and topic
            2. Be professional and business-appropriate
            3. Avoid text, logos, or specific people
            4. Use descriptive visual elements that represent the concept
            5. Be suitable for social media sharing

            Respond with exactly 2 prompts in this JSON format:
            {{
                "prompt1": "First image prompt here",
                "prompt2": "Second image prompt here"
            }}

            Make the prompts visually distinct but thematically related to the content.
            """

            # Generate prompts using Claude
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt_generation_request
                    }
                ],
                "temperature": 0.7
            }

            response = self.bedrock_client.invoke_model(
                modelId=self.text_model_id,
                body=json.dumps(request_body)
            )

            response_body = json.loads(response['body'].read())
            generated_prompts_text = response_body['content'][0]['text']

            # Parse the JSON response
            prompts_data = json.loads(generated_prompts_text)

            context_prompts = [
                prompts_data['prompt1'],
                prompts_data['prompt2']
            ]

            logger.info(f"Generated context-aware prompts: {context_prompts}")
            return context_prompts

        except Exception as e:
            logger.warning(f"Failed to generate context-aware prompts: {str(e)}")
            # Fallback to intelligent generic prompts based on keywords
            return self._create_fallback_prompts(text_content)

    def _create_fallback_prompts(self, text_content):
        """
        Create intelligent fallback prompts based on keyword analysis

        Args:
            text_content (str): The article content to analyze

        Returns:
            list: Two fallback image prompts
        """
        # Convert to lowercase for keyword matching
        content_lower = text_content.lower()

        # Define topic-based prompt templates
        topic_prompts = {
            'ai': [
                "Futuristic digital brain with neural network connections, glowing nodes and data streams, professional tech illustration with blue and purple gradients",
                "Abstract representation of artificial intelligence with geometric patterns, circuit boards, and flowing data visualizations in corporate colors"
            ],
            'technology': [
                "Modern technology workspace with connected devices, holographic displays, and digital interfaces, clean minimalist design",
                "Innovation concept with gears, digital networks, and technological growth symbols in professional blue tones"
            ],
            'business': [
                "Professional business meeting with diverse team, modern office setting, collaboration and growth symbols",
                "Corporate success visualization with charts, graphs, and upward trends in sophisticated color palette"
            ],
            'finance': [
                "Financial growth concept with rising charts, currency symbols, and investment graphics in gold and blue",
                "Professional banking and finance illustration with secure transactions and economic indicators"
            ],
            'marketing': [
                "Digital marketing concept with social media icons, engagement metrics, and brand connectivity illustrations",
                "Modern advertising and communication visualization with target audience and campaign elements"
            ],
            'leadership': [
                "Leadership and team management concept with organizational charts and collaborative elements",
                "Professional development and mentoring visualization with growth arrows and people connections"
            ],
            'innovation': [
                "Innovation and creativity concept with lightbulb, gears, and breakthrough visualization elements",
                "Cutting-edge research and development illustration with scientific and technological advancement themes"
            ]
        }

        # Check for keywords and select appropriate prompts (more specific matching)
        detected_topics = []
        for topic, prompts in topic_prompts.items():
            # Use word boundaries to avoid false matches
            import re
            pattern = r'\b' + topic + r'\b'
            if re.search(pattern, content_lower):
                detected_topics.append((topic, prompts))

        # Return prompts for the first detected topic
        if detected_topics:
            topic, prompts = detected_topics[0]
            logger.info(f"Detected topic '{topic}' - using targeted prompts")
            return prompts

        # Default professional prompts if no specific topic detected
        default_prompts = [
            "Professional business concept illustration with modern design elements, corporate colors, and innovation symbols",
            "Abstract professional graphic showing growth, success, and forward-thinking business strategy with geometric elements"
        ]

        logger.info("Using default professional prompts")
        return default_prompts

    def generate_single_image(self, prompt_text, model_type='nova'):
        """
        Generate a single image using specified model and prompt

        Args:
            prompt_text (str): The prompt to use for image generation
            model_type (str): 'nova' for Nova Canvas or 'titan' for Titan Image Generator

        Returns:
            dict: Generated image with 'success', 'image', 'prompt', and 'error' keys
        """
        try:
            logger.info(f"Starting single image generation with {model_type}")
            logger.info(f"Prompt text: {prompt_text[:100]}...")

            if model_type == 'nova':
                # Using Titan for Nova model type (same format as Titan)
                request_body = {
                    "taskType": "TEXT_IMAGE",
                    "textToImageParams": {
                        "text": prompt_text,
                        "negativeText": "blurry, low quality, distorted, unprofessional, nsfw"
                    },
                    "imageGenerationConfig": {
                        "numberOfImages": 1,
                        "height": 1024,
                        "width": 1024,
                        "cfgScale": 8.0,
                        "seed": 42
                    }
                }
                model_id = self.image_model_nova

            elif model_type == 'titan':
                # Titan G1 v2 request format
                request_body = {
                    "taskType": "TEXT_IMAGE",
                    "textToImageParams": {
                        "text": prompt_text,
                        "negativeText": "blurry, low quality, distorted, unprofessional, nsfw"
                    },
                    "imageGenerationConfig": {
                        "numberOfImages": 1,
                        "height": 1024,
                        "width": 1024,
                        "cfgScale": 7.5,
                        "seed": 43
                    }
                }
                model_id = self.image_model_titan
            else:
                error_msg = f"Unsupported model type: {model_type}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'image': None,
                    'prompt': prompt_text,
                    'error': error_msg
                }

            logger.info(f"Using model: {model_id}")
            logger.info(f"Request body: {json.dumps(request_body, indent=2)}")

            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )

            logger.info(f"Bedrock response status: {response.get('ResponseMetadata', {}).get('HTTPStatusCode', 'unknown')}")

            response_body = json.loads(response['body'].read())
            logger.info(f"Response body keys: {list(response_body.keys())}")

            if 'images' in response_body and len(response_body['images']) > 0:
                image_data = response_body['images'][0]
                logger.info(f"Successfully generated image with {model_type}")
                return {
                    'success': True,
                    'image': image_data,
                    'prompt': prompt_text,
                    'error': None
                }
            else:
                error_msg = f'No image generated with {model_type}. Response: {response_body}'
                logger.warning(error_msg)
                return {
                    'success': False,
                    'image': None,
                    'prompt': prompt_text,
                    'error': error_msg
                }

        except Exception as e:
            error_msg = f'Failed to generate image with {model_type}: {str(e)}'
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'image': None,
                'prompt': prompt_text,
                'error': error_msg
            }

    def generate_images(self, text_content, num_images=2):
        """
        Generate context-aware images using Nova Canvas and Titan Image Generator G1 v2

        Args:
            text_content (str): Text to base images on (summary or rationale)
            num_images (int): Number of images to generate (default 2)

        Returns:
            dict: Generated images with 'success', 'images', and 'error' keys
        """
        try:
            generated_images = []

            # Generate dynamic, context-aware prompts based on the article content
            prompts = self._create_context_aware_prompts(text_content)

            # Generate Image 1 with Nova Canvas
            if num_images >= 1:
                try:
                    # Nova Canvas request format
                    nova_request = {
                        "taskType": "TEXT_IMAGE",
                        "textToImageParams": {
                            "text": prompts[0]
                        },
                        "imageGenerationConfig": {
                            "numberOfImages": 1,
                            "quality": "standard",
                            "height": 1024,
                            "width": 1024,
                            "cfgScale": 8.0,
                            "seed": 42
                        }
                    }

                    response = self.bedrock_client.invoke_model(
                        modelId=self.image_model_nova,
                        body=json.dumps(nova_request)
                    )

                    response_body = json.loads(response['body'].read())

                    if 'images' in response_body and len(response_body['images']) > 0:
                        image_data = response_body['images'][0]
                        generated_images.append(image_data)
                        logger.info("Successfully generated image 1 with Nova Canvas")
                    else:
                        logger.warning("No image generated with Nova Canvas")
                        generated_images.append(None)

                except Exception as e:
                    logger.error(f"Error generating image with Nova Canvas: {str(e)}")
                    generated_images.append(None)

            # Generate Image 2 with Titan G1 v2
            if num_images >= 2:
                try:
                    # Titan G1 v2 request format
                    titan_request = {
                        "taskType": "TEXT_IMAGE",
                        "textToImageParams": {
                            "text": prompts[1],
                            "negativeText": "blurry, low quality, distorted, unprofessional, nsfw"
                        },
                        "imageGenerationConfig": {
                            "numberOfImages": 1,
                            "height": 1024,
                            "width": 1024,
                            "cfgScale": 7.5,
                            "seed": 43
                        }
                    }

                    response = self.bedrock_client.invoke_model(
                        modelId=self.image_model_titan,
                        body=json.dumps(titan_request)
                    )

                    response_body = json.loads(response['body'].read())

                    if 'images' in response_body and len(response_body['images']) > 0:
                        image_data = response_body['images'][0]
                        generated_images.append(image_data)
                        logger.info("Successfully generated image 2 with Titan Image Generator G1 v2")
                    else:
                        logger.warning("No image generated with Titan G1 v2")
                        generated_images.append(None)

                except Exception as e:
                    logger.error(f"Error generating image with Titan G1 v2: {str(e)}")
                    generated_images.append(None)

            # Filter out None values and check if we have any successful images
            valid_images = [img for img in generated_images if img is not None]

            if valid_images:
                return {
                    'success': True,
                    'images': generated_images,  # Keep original list with None values for proper indexing
                    'prompts': prompts,  # Include the generated prompts
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'images': [],
                    'prompts': prompts,  # Include prompts even if images failed
                    'error': 'Failed to generate any images'
                }

        except Exception as e:
            logger.error(f"Error in image generation: {str(e)}")
            return {
                'success': False,
                'images': [],
                'error': f'Failed to generate images: {str(e)}'
            }

    def create_markdown_content(self, post_data, image_urls=None):
        """
        Create formatted markdown content

        Args:
            post_data (dict): Generated post data with linkedin_post, summary, business_rationale
            image_urls (list): List of image URLs (optional)

        Returns:
            str: Formatted markdown content
        """
        markdown_content = f"""# LinkedIn Post Content

## LinkedIn Post
{post_data.get('linkedin_post', '')}

## Summary
{post_data.get('summary', '')}

## Business Rationale
{post_data.get('business_rationale', '')}
"""

        if image_urls:
            markdown_content += "\n## Generated Images\n"
            for i, url in enumerate(image_urls, 1):
                if url:
                    markdown_content += f"![Generated Image {i}]({url})\n\n"

        markdown_content += f"\n---\n*Generated on {self._get_current_timestamp()}*"

        return markdown_content

    def _get_current_timestamp(self):
        """Get current timestamp in readable format"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d at %H:%M UTC")


def generate_linkedin_content(scraped_content, user_prompt_adjustment=""):
    """
    Convenience function to generate LinkedIn content

    Args:
        scraped_content (str): Scraped article content
        user_prompt_adjustment (str): User's additional instructions

    Returns:
        dict: Generated content results
    """
    generator = AIGenerator()
    return generator.generate_text_content(scraped_content, user_prompt_adjustment)


def generate_content_images(text_content, num_images=2):
    """
    Convenience function to generate images

    Args:
        text_content (str): Text content to base images on
        num_images (int): Number of images to generate

    Returns:
        dict: Generated images results
    """
    generator = AIGenerator()
    return generator.generate_images(text_content, num_images)