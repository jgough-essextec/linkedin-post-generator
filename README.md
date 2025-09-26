# Link-to-LinkedIn Generator

A Django web application that transforms articles into professional LinkedIn posts using AWS Bedrock AI services. The application scrapes web content, generates AI-powered insights, creates relevant images, and produces ready-to-share LinkedIn content.

## Features

- 🔗 **Article Scraping**: Extracts main content from any web URL
- 🤖 **AI Content Generation**: Uses Claude (Anthropic) via AWS Bedrock to create professional LinkedIn posts
- 🎨 **Image Generation**: Creates relevant professional images using AWS Titan Image Generator
- 📝 **Multiple Outputs**: Generates LinkedIn post, summary, and business rationale
- 💾 **Cloud Storage**: Stores generated images in AWS S3
- 📄 **Export Options**: Download content as Markdown files
- 🌐 **Serverless Deployment**: Deploys to AWS Lambda using Zappa

## Tech Stack

- **Backend**: Django 4.2, Python 3.9
- **AI Services**: AWS Bedrock (Claude 3.5 Sonnet, Titan Image Generator)
- **Storage**: AWS S3, SQLite/PostgreSQL
- **Deployment**: AWS Lambda, Zappa
- **Frontend**: Bootstrap 5, HTML/CSS/JavaScript

## Installation

### Prerequisites

- Python 3.9+
- AWS Account with Bedrock access
- AWS CLI configured
- Node.js (for potential future enhancements)

### Local Development Setup

1. **Clone and Setup Environment**
   ```bash
   git clone <repository-url>
   cd linkedin-generator
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Database Setup**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database Configuration
DB_NAME=linkedin_generator
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
USE_POSTGRES=False  # Set to True for PostgreSQL

# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_STORAGE_BUCKET_NAME=linkedin-generator-images
AWS_REGION=us-east-1

# Django Configuration
DEBUG=True
SECRET_KEY=your_secret_key
USE_S3=False  # Set to True for S3 storage
```

## AWS Services Setup

### 1. AWS Bedrock Access

Ensure you have access to:
- **Claude 3.5 Sonnet** (anthropic.claude-3-5-sonnet-20241022-v2:0)
- **Titan Image Generator** (amazon.titan-image-generator-v2:0)

Request model access in the AWS Bedrock console if needed.

### 2. S3 Bucket Configuration

```bash
# Create S3 bucket for images
aws s3 mb s3://linkedin-generator-images

# Create S3 bucket for Zappa deployments
aws s3 mb s3://linkedin-generator-zappa-deployments
```

### 3. IAM Permissions

Your AWS user/role needs permissions for:
- Bedrock model invocation
- S3 bucket operations
- Lambda function management (for deployment)

## Deployment

### Development Deployment

```bash
# Activate virtual environment
source venv/bin/activate

# Deploy to AWS Lambda
zappa deploy dev

# Run migrations on deployed environment
zappa manage dev migrate
```

### Production Deployment

```bash
# Deploy to production
zappa deploy production

# Update environment variables in AWS Lambda console
# Set USE_POSTGRES=True and database credentials
# Run migrations
zappa manage production migrate
```

### Updating Deployments

```bash
# Update existing deployment
zappa update dev  # or production
```

## Usage

1. **Access the Application**
   - Local: `http://localhost:8000`
   - Deployed: Your Zappa deployment URL

2. **Generate LinkedIn Post**
   - Enter any article URL
   - Optionally customize the generation prompt
   - Click "Generate LinkedIn Post"
   - Wait 30-60 seconds for AI processing

3. **Review and Export**
   - Review the generated LinkedIn post
   - Copy the post text to clipboard
   - Download generated images
   - Export as Markdown file

## API Endpoints

- `/` - Main page (article URL input)
- `/generate/` - POST endpoint for generation
- `/result/<id>/` - View generated content
- `/download/markdown/<id>/` - Download Markdown file
- `/admin/` - Django admin interface

## Project Structure

```
linkedin-generator/
├── core/                   # Django project settings
│   ├── settings.py        # Main configuration
│   ├── urls.py           # URL routing
│   └── wsgi.py           # WSGI configuration
├── generator/             # Main Django app
│   ├── models.py         # GeneratedPost model
│   ├── views.py          # Main application views
│   ├── urls.py           # App URL patterns
│   ├── admin.py          # Admin interface
│   └── services/         # Business logic services
│       ├── scraper.py    # Web scraping service
│       ├── ai_generator.py # AI content generation
│       └── storage.py    # S3 storage service
├── templates/             # Django templates
│   ├── base.html         # Base template
│   └── generator/        # App-specific templates
├── requirements.txt       # Python dependencies
├── zappa_settings.json   # Zappa deployment config
└── .env.example          # Environment variables template
```

## Development

### Adding New Features

1. **Models**: Extend `generator/models.py` for new data structures
2. **Services**: Add new services in `generator/services/`
3. **Views**: Add new views in `generator/views.py`
4. **Templates**: Create new templates in `templates/generator/`

### Testing

```bash
# Run Django tests
python manage.py test

# Check for issues
python manage.py check
```

### Database Migrations

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# For deployed environments
zappa manage dev migrate
```

## Troubleshooting

### Common Issues

1. **AWS Bedrock Access Denied**
   - Ensure your region supports Bedrock
   - Request model access in Bedrock console
   - Verify IAM permissions

2. **Image Upload Failures**
   - Check S3 bucket permissions
   - Verify AWS credentials
   - Ensure bucket exists in correct region

3. **Deployment Issues**
   - Check Zappa logs: `zappa tail dev`
   - Verify AWS credentials
   - Ensure all dependencies are in requirements.txt

### Logs and Debugging

```bash
# View Zappa logs
zappa tail dev --since 1h

# Check Django logs (local)
# Logs are printed to console during development

# Debug mode
# Set DEBUG=True in .env for detailed error messages
```

## Security Considerations

- Never commit AWS credentials to version control
- Use environment variables for sensitive data
- Set `DEBUG=False` in production
- Implement proper error handling for production use
- Consider implementing rate limiting for public deployments

## Cost Optimization

- **AWS Bedrock**: Pay per API call
- **Lambda**: Pay per invocation and duration
- **S3**: Pay for storage and requests
- **CloudWatch**: Monitor logs and metrics

To optimize costs:
- Implement caching for repeated requests
- Use appropriate Lambda memory allocation
- Clean up old S3 objects periodically
- Monitor usage with AWS Cost Explorer

## Future Enhancements

- [ ] User authentication and post history
- [ ] Async task processing with SQS/Celery
- [ ] Multiple AI model options
- [ ] Post scheduling integration
- [ ] Analytics and usage metrics
- [ ] Batch processing capabilities
- [ ] Custom image styles/themes

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review AWS Bedrock documentation
3. Check Django documentation
4. Open an issue on GitHub

---

**Note**: This application requires AWS Bedrock access and may incur costs based on usage. Review AWS pricing for Bedrock, Lambda, and S3 services before deployment.