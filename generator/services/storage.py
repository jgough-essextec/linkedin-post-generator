import boto3
import base64
import uuid
import json
import logging
from django.conf import settings
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3StorageService:
    """Service for uploading files to AWS S3"""

    def __init__(self):
        # Configure boto3 client - prefer IAM role credentials in Lambda environment
        import os

        client_kwargs = {
            'region_name': getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1'),
        }

        # Check if we're running in Lambda environment
        if 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
            # In Lambda, use IAM role credentials (default credential chain)
            logger.info("Using IAM role credentials for S3 in Lambda environment")
        else:
            # Local development - use explicit credentials if available
            access_key = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
            secret_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)

            if access_key and secret_key:
                client_kwargs['aws_access_key_id'] = access_key
                client_kwargs['aws_secret_access_key'] = secret_key
                logger.info("Using explicit credentials for S3 in local environment")

        self.s3_client = boto3.client('s3', **client_kwargs)
        self.bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'linkedin-generator-images')

    def upload_image(self, image_data, file_prefix="generated_image", file_extension="png"):
        """
        Upload an image to S3

        Args:
            image_data (str): Base64 encoded image data
            file_prefix (str): Prefix for the filename
            file_extension (str): File extension

        Returns:
            dict: Upload result with 'success', 'url', and 'error' keys
        """
        try:
            # Decode base64 image data
            if isinstance(image_data, str):
                # Remove data URL prefix if present
                if image_data.startswith('data:'):
                    image_data = image_data.split(',')[1]

                image_bytes = base64.b64decode(image_data)
            else:
                image_bytes = image_data

            # Generate unique filename
            unique_id = str(uuid.uuid4())
            filename = f"images/{file_prefix}_{unique_id}.{file_extension}"

            # Set content type based on extension
            content_type_map = {
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'gif': 'image/gif',
                'webp': 'image/webp'
            }
            content_type = content_type_map.get(file_extension.lower(), 'image/png')

            # Upload to S3 (remove ACL since bucket doesn't allow ACLs)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=filename,
                Body=image_bytes,
                ContentType=content_type
                # Note: Public access is managed via bucket policy instead of ACL
            )

            # Generate public URL
            image_url = f"https://{self.bucket_name}.s3.{getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1')}.amazonaws.com/{filename}"

            return {
                'success': True,
                'url': image_url,
                'filename': filename,
                'error': None
            }

        except Exception as e:
            logger.error(f"Error uploading image to S3: {str(e)}")
            return {
                'success': False,
                'url': None,
                'filename': None,
                'error': f'Failed to upload image: {str(e)}'
            }

    def upload_multiple_images(self, image_data_list, file_prefix="generated_image"):
        """
        Upload multiple images to S3

        Args:
            image_data_list (list): List of base64 encoded image data
            file_prefix (str): Prefix for filenames

        Returns:
            dict: Upload results with 'success', 'urls', and 'errors' keys
        """
        results = []
        urls = []
        errors = []

        for i, image_data in enumerate(image_data_list):
            result = self.upload_image(
                image_data,
                f"{file_prefix}_{i+1}"
            )

            results.append(result)

            if result['success']:
                urls.append(result['url'])
            else:
                errors.append(result['error'])

        return {
            'success': len(urls) > 0,
            'urls': urls,
            'errors': errors,
            'results': results
        }

    def create_bucket_if_not_exists(self):
        """
        Create S3 bucket if it doesn't exist

        Returns:
            dict: Operation result
        """
        try:
            # Check if bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)

            return {
                'success': True,
                'message': f'Bucket {self.bucket_name} already exists',
                'error': None
            }

        except ClientError as e:
            error_code = int(e.response['Error']['Code'])

            if error_code == 404:
                # Bucket doesn't exist, create it
                try:
                    region = getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1')

                    if region == 'us-east-1':
                        # us-east-1 doesn't need LocationConstraint
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': region}
                        )

                    # Configure bucket for public read access
                    self._configure_bucket_policy()

                    return {
                        'success': True,
                        'message': f'Bucket {self.bucket_name} created successfully',
                        'error': None
                    }

                except ClientError as create_error:
                    logger.error(f"Error creating bucket: {str(create_error)}")
                    return {
                        'success': False,
                        'message': None,
                        'error': f'Failed to create bucket: {str(create_error)}'
                    }
            else:
                logger.error(f"Error accessing bucket: {str(e)}")
                return {
                    'success': False,
                    'message': None,
                    'error': f'Error accessing bucket: {str(e)}'
                }

    def _configure_bucket_policy(self):
        """Configure bucket policy for public read access to images"""
        try:
            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "PublicReadGetObject",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:GetObject",
                        "Resource": f"arn:aws:s3:::{self.bucket_name}/images/*"
                    }
                ]
            }

            self.s3_client.put_bucket_policy(
                Bucket=self.bucket_name,
                Policy=json.dumps(bucket_policy)
            )

            logger.info(f"Bucket policy configured for {self.bucket_name}")

        except Exception as e:
            logger.warning(f"Could not set bucket policy: {str(e)}")

    def delete_file(self, filename):
        """
        Delete a file from S3

        Args:
            filename (str): The key/filename to delete

        Returns:
            dict: Deletion result
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=filename
            )

            return {
                'success': True,
                'error': None
            }

        except Exception as e:
            logger.error(f"Error deleting file {filename}: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to delete file: {str(e)}'
            }


def upload_image_to_s3(image_data, file_prefix="generated_image"):
    """
    Convenience function to upload an image to S3

    Args:
        image_data (str): Base64 encoded image data
        file_prefix (str): Prefix for the filename

    Returns:
        dict: Upload result
    """
    storage_service = S3StorageService()
    return storage_service.upload_image(image_data, file_prefix)


def upload_multiple_images_to_s3(image_data_list, file_prefix="generated_image"):
    """
    Convenience function to upload multiple images to S3

    Args:
        image_data_list (list): List of base64 encoded image data
        file_prefix (str): Prefix for filenames

    Returns:
        dict: Upload results
    """
    storage_service = S3StorageService()
    return storage_service.upload_multiple_images(image_data_list, file_prefix)