# TODO: LinkedIn Post Generator Application

This document outlines the tasks required to build, and deploy the "Link-to-LinkedIn" Django application.

## Phase 1: Project Setup & Configuration

- [ ] **Initialize Project Environment**
    - [ ] Create a project directory.
    - [ ] Set up a Python virtual environment (`python -m venv venv`).
    - [ ] Activate the virtual environment (`source venv/bin/activate`).
    - [ ] Create a `requirements.txt` file.

- [ ] **Install Dependencies**
    - [ ] Add and install core dependencies:
        - `django` (for the web framework)
        - `psycopg2-binary` (for PostgreSQL connection)
        - `zappa` (for AWS Lambda deployment)
        - `boto3` (for AWS SDK, specifically for Bedrock)
        - `requests` (to fetch URL content)
        - `beautifulsoup4` (to parse HTML from the URL)
        - `python-dotenv` (to manage environment variables)

- [ ] **Initialize Django Project**
    - [ ] Create the Django project (`django-admin startproject core .`).
    - [ ] Create the main application (`python manage.py startapp generator`).
    - [ ] Add `generator` to `INSTALLED_APPS` in `core/settings.py`.

- [ ] **Configure Database**
    - [ ] Set up a local PostgreSQL database.
    - [ ] Configure `DATABASES` in `core/settings.py` to connect to the PostgreSQL instance. Use environment variables for credentials.

- [ ] **AWS & Zappa Configuration**
    - [ ] Configure AWS credentials locally (`~/.aws/credentials`) for Boto3 and Zappa to use.
    - [ ] Run `zappa init` to generate `zappa_settings.json`. Configure the Django project settings.
    - [ ] Create an S3 bucket to store generated images.

## Phase 2: Core Models & Database Schema

- [ ] **Define the `GeneratedPost` Model** in `generator/models.py`
    - [ ] `source_url`: `URLField` to store the original article URL.
    - [ ] `original_content`: `TextField` to store the scraped text from the URL.
    - [ ] `user_prompt_adjustment`: `TextField` for the user's prompt modifications (can be blank).
    - [ ] `linkedin_post`: `TextField` for the generated post text.
    - [ ] `summary`: `TextField` for the generated summary.
    - [ ] `business_rationale`: `TextField` for the importance rationale.
    - [ ] `image_url_1`: `URLField` pointing to the first generated image in S3.
    - [ ] `image_url_2`: `URLField` pointing to the second generated image in S3.
    - [ ] `markdown_content`: `TextField` to store the complete markdown output.
    - [ ] `created_at`: `DateTimeField` with `auto_now_add=True`.

- [ ] **Run Database Migrations**
    - [ ] `python manage.py makemigrations generator`
    - [ ] `python manage.py migrate`

## Phase 3: Backend Logic & Service Layer

- [ ] **Create a Content Scraping Service** (`generator/services/scraper.py`)
    - [ ] Create a function that takes a URL, uses `requests` to fetch the HTML.
    - [ ] Use `BeautifulSoup4` to parse the HTML and extract the main article text, stripping out boilerplate (nav, ads, etc.).
    - [ ] Implement error handling for invalid URLs or failed requests.

- [ ] **Create an AI Generation Service** (`generator/services/ai_generator.py`)
    - [ ] **Initialize Boto3 Bedrock Client**: Create a reusable client for the AWS Bedrock runtime.
    - [ ] **Text Generation Function**:
        - [ ] Takes the scraped text and user prompt as input.
        - [ ] Constructs a detailed prompt for the Anthropic Claude model. The prompt should ask for a structured JSON output containing `linkedin_post`, `summary`, and `business_rationale`.
        - [ ] Invokes the model via the Bedrock API.
        - [ ] Parses the JSON response from Claude.
    - [ ] **Image Generation Function**:
        - [ ] Takes the summary or rationale as input.
        - [ ] Constructs two distinct prompts for an image generation model available in Bedrock (e.g., Amazon Titan Image Generator).
        - [ ] Invokes the model twice to get two image options (likely returned as base64 encoded strings).
        - [ ] Implement error handling for API failures.

- [ ] **Create an S3 Storage Service** (`generator/services/storage.py`)
    - [ ] Create a function to upload a file (the generated image) to a specified S3 bucket.
    - [ ] The function should accept the image data (decoded from base64), generate a unique filename, and upload it.
    - [ ] It should return the public URL of the uploaded image.

## Phase 4: Django Views & URLS

- [ ] **Define URLs** in `generator/urls.py`
    - [ ] `/`: The main page for submitting a URL (`index_view`).
    - [ ] `/generate`: The endpoint to handle the form submission (POST request) (`generate_view`).
    - [ ] `/result/<int:post_id>/`: The page to display the generated content (`result_view`).
    - [ ] `/download/markdown/<int:post_id>/`: Endpoint to trigger a download of the markdown file.
    - [ ] Include `generator.urls` in the main `core/urls.py`.

- [ ] **Implement Views** in `generator/views.py`
    - [ ] **`index_view`**: Renders the main form template.
    - [ ] **`generate_view`**:
        - [ ] Handles POST requests.
        - [ ] Calls the scraper service to get content.
        - [ ] Calls the AI service to generate text and images.
        - [ ] Calls the S3 service to store the images.
        - [ ] Creates and saves a `GeneratedPost` model instance to the database.
        - [ ] Redirects the user to the `result_view` with the new post's ID.
    - [ ] **`result_view`**:
        - [ ] Fetches the `GeneratedPost` object from the DB using the `post_id`.
        - [ ] Renders the result template, passing the post object as context.
    - [ ] **`download_markdown_view`**:
        - [ ] Fetches the `GeneratedPost` object.
        - [ ] Creates an `HttpResponse` with the markdown content.
        - [ ] Sets the `Content-Disposition` header to trigger a file download.

## Phase 5: Frontend (Templates)

- [ ] **Create a Base Template** (`templates/base.html`)
    - [ ] Include basic HTML structure, head tags, and links to CSS/JS frameworks (e.g., Bootstrap for simplicity).
    - [ ] Define content blocks for other templates to extend.

- [ ] **Create the Index Template** (`templates/generator/index.html`)
    - [ ] A form with a single text input for the URL.
    - [ ] A textarea for adjusting the standard prompt (pre-filled with a default prompt).
    - [ ] A "Generate" submit button.

- [ ] **Create the Result Template** (`templates/generator/result.html`)
    - [ ] Display the generated LinkedIn post, summary, and rationale clearly.
    - [ ] Display the two generated images (`<img>` tags pointing to the S3 URLs).
    - [ ] Provide a "Download Markdown" link pointing to the download URL.
    - [ ] Provide "Download Image 1" and "Download Image 2" links (these can be simple `<a>` tags pointing to the S3 URLs with a `download` attribute).

## Phase 6: Deployment with Zappa

- [ ] **Finalize `zappa_settings.json`**
    - [ ] Ensure the Django settings path is correct.
    - [ ] Set up environment variables needed by the application (DB credentials, S3 bucket name, AWS region).
    - [ ] Configure a `manage` command alias to run migrations remotely.

- [ ] **Static File Handling**
    - [ ] Configure Django to serve static files from S3 for production (e.g., using `django-storages`). This is crucial for CSS/JS on Lambda.

- [ ] **Deploy and Test**
    - [ ] Run `zappa deploy <stage>` (e.g., `dev`).
    - [ ] Run remote database migrations: `zappa manage <stage> migrate`.
    - [ ] Test the live application endpoint.

## Phase 7: Future Enhancements & Polish

- [ ] **Add User Authentication**: To allow users to see a history of their generated posts.
- [ ] **Asynchronous Task Processing**: For long-running AI generations, use SQS/Celery to process tasks in the background so the user doesn't have to wait.
- [ ] **Improve UI/UX**: Add loading indicators, better feedback on form submission, and a more polished design.
- [ ] **Error Handling**: Add more robust error handling and user-facing error messages (e.g., "This URL could not be processed.").
- [ ] **Logging**: Implement proper logging to monitor the application on AWS Lambda (CloudWatch).
