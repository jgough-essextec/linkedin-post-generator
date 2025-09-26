from django.db import models


class GeneratedPost(models.Model):
    source_url = models.URLField(max_length=2048, help_text="Original article URL")
    original_content = models.TextField(help_text="Scraped text from the URL")
    user_prompt_adjustment = models.TextField(
        blank=True,
        null=True,
        help_text="User's prompt modifications"
    )
    linkedin_post = models.TextField(help_text="Generated LinkedIn post text")
    summary = models.TextField(help_text="Generated summary")
    business_rationale = models.TextField(help_text="Business importance rationale")
    image_url_1 = models.URLField(
        max_length=2048,
        blank=True,
        null=True,
        help_text="First generated image in S3"
    )
    image_url_2 = models.URLField(
        max_length=2048,
        blank=True,
        null=True,
        help_text="Second generated image in S3"
    )
    markdown_content = models.TextField(help_text="Complete markdown output")
    images_processing = models.BooleanField(default=False, help_text="Whether images are currently being generated")
    images_completed_at = models.DateTimeField(null=True, blank=True, help_text="When image generation completed")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Generated Post"
        verbose_name_plural = "Generated Posts"

    def __str__(self):
        return f"Post from {self.source_url} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
