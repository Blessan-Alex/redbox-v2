# Model Configuration Guide

This guide explains how to configure different model names in Redbox.

## Overview

In Redbox, there are two levels of configuration:

1. **Environment Variables** (`.env` file) - Set the LLM provider and API key
2. **Database Configuration** - Set the specific model name and parameters

## Current Configuration

Your current setup:
- **Provider**: Google Gemini (`google_genai`)
- **Model**: `gemini-2.0-flash`
- **API Key**: Set in `.env` file as `GOOGLE_API_KEY`

## How to Change Model Names

### Method 1: Django Admin Interface (Recommended)

1. **Access Admin Panel**
   ```
   http://localhost:8090/admin/
   ```

2. **Navigate to Model Configuration**
   - Go to "Redbox core" → "Chat LLM backends"
   - Click on the default backend (usually the first one)

3. **Change Model Name**
   - Edit the "Name" field
   - Save the changes

### Method 2: Django Shell Command

```bash
# Check current model
docker compose exec django-app venv/bin/django-admin shell -c "
from redbox_app.redbox_core.models import ChatLLMBackend
backend = ChatLLMBackend.objects.get(is_default=True)
print(f'Current: {backend.name}')
"

# Change to different model
docker compose exec django-app venv/bin/django-admin shell -c "
from redbox_app.redbox_core.models import ChatLLMBackend
backend = ChatLLMBackend.objects.get(is_default=True)
backend.name = 'gemini-1.5-flash'
backend.save()
print(f'Updated to: {backend.name}')
"
```

## Available Gemini Models

| Model Name | Description | Use Case |
|------------|-------------|----------|
| `gemini-2.0-flash` | Latest, fast, efficient | **Recommended** - Best balance |
| `gemini-1.5-flash` | Fast, good capability | Good for quick responses |
| `gemini-1.5-pro` | More capable, slower | Better for complex tasks |
| `gemini-pro` | Original model | Legacy compatibility |

## Other LLM Providers

### OpenAI Models
- `gpt-4o` (GPT-4 Omni)
- `gpt-4o-mini`
- `gpt-4-turbo`
- `gpt-3.5-turbo`

### Azure OpenAI Models
- `gpt-4o`
- `gpt-4-turbo`
- `gpt-35-turbo`

## Verification

After changing the model, verify it's working:

```bash
# Check current configuration
docker compose exec django-app venv/bin/django-admin shell -c "
from redbox_app.redbox_core.models import ChatLLMBackend
backend = ChatLLMBackend.objects.get(is_default=True)
print(f'Model: {backend.name}')
print(f'Provider: {backend.provider}')
print(f'Default: {backend.is_default}')
"
```

## Troubleshooting

### Model Not Working
1. **Check API Key**: Ensure `GOOGLE_API_KEY` is set correctly
2. **Restart Container**: `docker compose restart django-app`
3. **Check Logs**: `docker compose logs django-app`

### Model Name Not Recognized
- Verify the model name is correct (check Google AI Studio for latest names)
- Ensure the provider is set to `google_genai` for Gemini models

### Performance Issues
- Try a different model (e.g., switch from `gemini-1.5-pro` to `gemini-2.0-flash`)
- Check your API quota and rate limits
