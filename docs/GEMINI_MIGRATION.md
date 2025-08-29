# Migrating from OpenAI to Gemini in Redbox

This document outlines the steps to successfully migrate from OpenAI/Azure OpenAI to Google Gemini in the Redbox project.

## Prerequisites

- Google Generative AI API key
- Access to the Redbox project codebase
- Docker and Docker Compose installed

## Step 1: Add Required Dependencies

### 1.1 Update Python Dependencies

Add the `langchain-google-genai` package to `django_app/pyproject.toml`:

```toml
[tool.poetry.dependencies]
# ... existing dependencies ...
langchain-google-genai = "^2.0.13"
```

### 1.2 Update Poetry Lock File

```bash
cd django_app
poetry lock
```

### 1.3 Rebuild Docker Container

```bash
docker compose build django-app
```

## Step 2: Configure Environment Variables

### 2.1 Update .env File

Replace or add the following environment variables in your `.env` file:

```bash
# Remove or comment out Azure OpenAI settings
# AZURE_OPENAI_MODEL=
# AZURE_OPENAI_API_KEY=
# AZURE_OPENAI_ENDPOINT=

# Add Google Gemini settings
GOOGLE_API_KEY=your_google_api_key_here
```

**Important**: Use `GOOGLE_API_KEY` (not `GOOGLE_GENERATIVE_AI_API_KEY`)

## Step 3: Update Database Configuration

### 3.1 Create Migration to Update Default Backend

Create a new Django migration to update the default ChatLLMBackend:

```bash
docker compose exec django-app venv/bin/django-admin makemigrations redbox_core --name update_default_backend_to_gemini --empty
```

### 3.2 Edit the Migration File

Edit the generated migration file (e.g., `django_app/redbox_app/redbox_core/migrations/0094_update_default_backend_to_gemini.py`):

```python
# Generated manually to update default backend to Gemini

from django.db import migrations


def update_default_backend_to_gemini(apps, schema_editor):
    """Update the default ChatLLMBackend to use Gemini instead of Azure OpenAI."""
    ChatLLMBackend = apps.get_model("redbox_core", "ChatLLMBackend")
    
    # Find the default backend
    try:
        default_backend = ChatLLMBackend.objects.get(is_default=True)
        # Update it to use Gemini
        default_backend.name = "gemini-2.0-flash"  # Can be: gemini-2.0-flash, gemini-1.5-flash, gemini-1.5-pro, gemini-pro
        default_backend.provider = "google_genai"
        default_backend.description = "Google Gemini 2.0 Flash model"
        default_backend.context_window_size = 128000
        default_backend.save()
        print(f"Updated default backend to: {default_backend.name} ({default_backend.provider})")
    except ChatLLMBackend.DoesNotExist:
        print("No default backend found")


def reverse_update_default_backend_to_gemini(apps, schema_editor):
    """Reverse the migration - change back to Azure OpenAI."""
    ChatLLMBackend = apps.get_model("redbox_core", "ChatLLMBackend")
    
    try:
        default_backend = ChatLLMBackend.objects.get(is_default=True)
        default_backend.name = "gpt-4o"
        default_backend.provider = "azure_openai"
        default_backend.description = "Azure OpenAI GPT-4o model"
        default_backend.context_window_size = 128000
        default_backend.save()
        print(f"Reverted default backend to: {default_backend.name} ({default_backend.provider})")
    except ChatLLMBackend.DoesNotExist:
        print("No default backend found")


class Migration(migrations.Migration):
    dependencies = [
        ('redbox_core', '0093_previous_migration'),  # Replace with actual previous migration
    ]

    operations = [
        migrations.RunPython(
            update_default_backend_to_gemini,
            reverse_update_default_backend_to_gemini
        ),
    ]
```

### 3.3 Run the Migration

```bash
docker compose exec django-app venv/bin/django-admin migrate redbox_core 0094
```

## Step 4: Restart Services

### 4.1 Restart Django Container

After updating environment variables, restart the Django container to pick up changes:

```bash
docker compose down django-app
docker compose up -d django-app
```

### 4.2 Verify Configuration

Check that the environment variable is correctly set:

```bash
docker compose exec django-app env | grep GOOGLE_API_KEY
```

Expected output:
```
GOOGLE_API_KEY=your_google_api_key_here
```

## Step 5: Verify Migration

### 5.1 Check Database Configuration

Verify the default backend has been updated:

```bash
docker compose exec django-app venv/bin/django-admin shell -c "from redbox_app.redbox_core.models import ChatLLMBackend; backend = ChatLLMBackend.objects.get(is_default=True); print(f'Default backend: {backend.name} ({backend.provider})')"
```

Expected output:
```
Default backend: gemini-2.0-flash (google_genai)
```

### 5.2 Test Chat Functionality

1. Access the Redbox application at `http://localhost:8090`
2. Create a new chat or use an existing one
3. Send a test message
4. Verify that the response comes from Gemini

## Troubleshooting

### Common Issues

1. **Environment Variable Not Picked Up**
   - Ensure you're using `GOOGLE_API_KEY` (not `GOOGLE_GENERATIVE_AI_API_KEY`)
   - Restart the Django container after changing environment variables

2. **Missing Dependencies**
   - Ensure `langchain-google-genai` is added to `pyproject.toml`
   - Run `poetry lock` and rebuild the Docker container

3. **Database Migration Issues**
   - Check that the migration file is correctly formatted
   - Verify the migration number matches the actual file

4. **Authentication Errors**
   - Verify your Google API key is valid
   - Ensure the API key has access to Google Generative AI

### Debugging Commands

```bash
# Check container status
docker compose ps

# View Django logs
docker compose logs django-app

# Check environment variables
docker compose exec django-app env | grep GOOGLE

# Test database connection
docker compose exec django-app venv/bin/django-admin check --database default
```

## Summary

The migration from OpenAI to Gemini involves:

1. **Adding the `langchain-google-genai` dependency**
2. **Setting the `GOOGLE_API_KEY` environment variable**
3. **Updating the database to use Gemini as the default backend**
4. **Restarting services to pick up changes**

This approach ensures that the application dynamically uses the database configuration, making it easy to switch between different LLM providers without code changes.
