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

## Step 2: Configure Environment Variables (REQUIRED)

### 2.1 Update .env File

**This step is MANDATORY** - you must set the Google API key before proceeding with any migration method.

Replace or add the following environment variables in your `.env` file:

```bash
# Remove or comment out Azure OpenAI settings
# AZURE_OPENAI_MODEL=
# AZURE_OPENAI_API_KEY=
# AZURE_OPENAI_ENDPOINT=

# Add Google Gemini settings (REQUIRED)
GOOGLE_API_KEY=your_google_api_key_here
```

**Important**: 
- Use `GOOGLE_API_KEY` (not `GOOGLE_GENERATIVE_AI_API_KEY`)
- This environment variable is **MANDATORY** for all migration methods
- You must restart the Django container after setting this: `docker compose restart django-app`

## Step 3: Choose Migration Method

After setting the `GOOGLE_API_KEY`, choose one of these four methods to complete the migration:

## 🎯 Method 1: Django Admin Interface (Recommended)

1. Access Admin Panel: Go to http://localhost:8090/admin/
2. Navigate to: "Redbox core" → "Chat LLM backends"
3. Edit the default backend and change the model name
4. Save changes

## 🛠️ Method 2: Django Shell Commands

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

## ⚙️ Method 3: Additional Environment Variables (Optional)

If you want to switch between different providers later, you can set these additional environment variables in your .env file:

```bash
# For OpenAI (if switching from Gemini)
OPENAI_API_KEY=your_api_key_here

# For Azure OpenAI (if switching from Gemini)
AZURE_OPENAI_MODEL=azure/your_deployment_name
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=your_endpoint

# For Anthropic Claude (if switching from Gemini)
ANTHROPIC_API_KEY=your_api_key_here
```

**Note**: The `GOOGLE_API_KEY` is still required and should already be set from Step 2.

## 📊 Method 4: Database Migration

Create a Django migration to update the default backend:

```bash
# Create migration
docker compose exec django-app venv/bin/django-admin makemigrations redbox_core --name update_llm_backend --empty

# Edit the migration file to update the model
# Then run:
docker compose exec django-app venv/bin/django-admin migrate
```

## 🤖 Available Models by Provider

### Google Gemini Models
- gemini-2.0-flash (Latest, recommended)
- gemini-1.5-flash (Fast, good capability)
- gemini-1.5-pro (More capable, slower)
- gemini-pro (Legacy)

### OpenAI Models
- gpt-4o (GPT-4 Omni)
- gpt-4o-mini
- gpt-4-turbo
- gpt-3.5-turbo

### Azure OpenAI Models
- azure/gpt-4o
- azure/gpt-4-turbo
- azure/gpt-35-turbo

## 🔍 Current Configuration

Looking at your code, the default configuration is:
- Provider: google_genai (Google Gemini)
- Model: gemini-2.0-flash
- Context Window: 128,000 tokens

## ✅ Verification

After changing, verify it's working:

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

## 🚨 Important Notes

1. Model names are configured in the database, not environment variables
2. Environment variables only set the API keys and provider
3. Restart the Django container after making changes: `docker compose restart django-app`
4. Check logs if issues: `docker compose logs django-app`

The Django Admin Interface (Method 1) is the easiest and most user-friendly way to change models, while Django Shell (Method 2) is great for automation and scripting.

## Step 4: Update Database Configuration (If using Method 4)

### 4.1 Create Migration to Update Default Backend

Create a new Django migration to update the default ChatLLMBackend:

```bash
docker compose exec django-app venv/bin/django-admin makemigrations redbox_core --name update_default_backend_to_gemini --empty
```

### 4.2 Complete Migration Script

Here's the complete migration script to update the default backend to Gemini:

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

### 4.3 Run the Migration

```bash
docker compose exec django-app venv/bin/django-admin migrate redbox_core 0094
```

## Step 5: Update redbox.py Implementation

You need to update the `redbox.py` file to use the gemini implementation compared to the old one. Here's the updated version:

### Current redbox.py (Updated Implementation)

```python
from functools import cache

import boto3
import datetime
import tiktoken
from _datetime import timedelta
from langchain.chat_models import init_chat_model
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, AnyMessage, BaseMessage
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ChatLLMBackend(BaseModel):
    name: str = "gemini-2.0-flash"
    provider: str = "google_genai"
    description: str | None = None
    context_window_size: int = 128_000
    model_config = {"frozen": True}


class Settings(BaseSettings):
    """Settings for the redbox application."""

    minio_host: str = "minio"
    minio_port: int = 9000
    aws_access_key: str | None = None
    aws_secret_key: str | None = None

    aws_region: str = "eu-west-2"
    bucket_name: str = "redbox-storage-dev"

    object_store: str = "minio"

    system_prompt_template: str = """You are Redbox, an AI assistant to civil servants in the United Kingdom.

You follow instructions and respond to queries accurately and concisely, and are professional in all your
interactions with users. You use British English spellings and phrases rather than American English.

{% if documents is defined and documents|length > 0 %}
Use the following documents as primary sources for information and use them to respond to the users queries

{% for d in documents %}
Title: {{d.metadata.get("uri", "unknown document")}}
{{d.page_content}}

{% endfor %}
{% endif %}
"""

    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__", extra="allow", frozen=True)

    def s3_client(self):
        if self.object_store == "minio":
            return boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key or "",
                aws_secret_access_key=self.aws_secret_key or "",
                endpoint_url=f"http://{self.minio_host}:{self.minio_port}",
            )

        if self.object_store == "s3":
            return boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region,
            )

        msg = f"unknown object_store={self.object_store}"
        raise NotImplementedError(msg)


@cache
def get_tokeniser() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


class RedboxState(BaseModel):
    documents: list[Document] = Field(description="List of files to process", default_factory=list)
    messages: list[AnyMessage] = Field(description="All previous messages in chat", default_factory=list)
    chat_backend: ChatLLMBackend = Field(description="User request AI settings", default_factory=ChatLLMBackend)

    def get_llm(self):
        if self.chat_backend.provider == "google_vertexai":
            return init_chat_model(
                model=self.chat_backend.name,
                model_provider=self.chat_backend.provider,
                location="europe-west1",
                # europe-west1 = Belgium
            )
        elif self.chat_backend.provider == "google_genai":
            return init_chat_model(
                model=self.chat_backend.name,
                model_provider=self.chat_backend.provider,
            )
        return init_chat_model(
            model=self.chat_backend.name,
            model_provider=self.chat_backend.provider,
        )

    def get_messages(self) -> list[BaseMessage]:
        settings = Settings()

        input_state = self.model_dump()
        system_messages = (
            PromptTemplate.from_template(settings.system_prompt_template, template_format="jinja2")
            .invoke(input=input_state)
            .to_messages()
        )
        return system_messages + self.messages


async def _default_callback(*args, **kwargs):
    return None


def run_sync(state: RedboxState) -> tuple[BaseMessage, timedelta]:
    """
    Run Redbox without streaming events. This simpler, synchronous execution enables use of the graph debug logging
    """
    start = datetime.datetime.now()
    result = state.get_llm().invoke(input=state.get_messages())
    end = datetime.datetime.now()
    return result, end - start


async def run_async(
    state: RedboxState,
    response_tokens_callback=_default_callback,
) -> tuple[AIMessage, timedelta]:
    start = datetime.datetime.now()
    end = None
    final_message = ""
    async for event in state.get_llm().astream_events(
        state.get_messages(),
        version="v2",
    ):
        if event["event"] == "on_chat_model_stream":
            if end is None:
                end = datetime.datetime.now()
            content = event["data"]["chunk"].content
            final_message += content
            await response_tokens_callback(content)
    return AIMessage(content=final_message), end - start
```

### Old redbox.py (Previous Implementation)

```python
import os
from functools import cache

import boto3
import datetime
import tiktoken
from _datetime import timedelta
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, AnyMessage, BaseMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ChatLLMBackend(BaseModel):
    name: str = "gpt-4o"
    provider: str = "azure_openai"
    description: str | None = None
    context_window_size: int = 128_000
    model_config = {"frozen": True}


class Settings(BaseSettings):
    """Settings for the redbox application."""

    minio_host: str = "minio"
    minio_port: int = 9000
    aws_access_key: str | None = None
    aws_secret_key: str | None = None

    aws_region: str = "eu-west-2"
    bucket_name: str = "redbox-storage-dev"

    object_store: str = "minio"

    system_prompt_template: str = """You are Redbox, an AI assistant to civil servants in the United Kingdom.

You follow instructions and respond to queries accurately and concisely, and are professional in all your
interactions with users. You use British English spellings and phrases rather than American English.

{% if documents is defined and documents|length > 0 %}
Use the following documents as primary sources for information and use them to respond to the users queries

{% for d in documents %}
Title: {{d.metadata.get("uri", "unknown document")}}
{{d.page_content}}

{% endfor %}
{% endif %}
"""

    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__", extra="allow", frozen=True)

    def s3_client(self):
        if self.object_store == "minio":
            return boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key or "",
                aws_secret_access_key=self.aws_secret_key or "",
                endpoint_url=f"http://{self.minio_host}:{self.minio_port}",
            )

        if self.object_store == "s3":
            return boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region,
            )

        msg = f"unknown object_store={self.object_store}"
        raise NotImplementedError(msg)


@cache
def get_tokeniser() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


class RedboxState(BaseModel):
    documents: list[Document] = Field(description="List of files to process", default_factory=list)
    messages: list[AnyMessage] = Field(description="All previous messages in chat", default_factory=list)
    chat_backend: ChatLLMBackend = Field(description="User request AI settings", default_factory=ChatLLMBackend)

    def get_llm(self):
        api_key = os.environ["LITELLM_PROXY_API_KEY"]
        base_url = os.environ["LITELLM_PROXY_API_BASE"]
        return ChatOpenAI(model=self.chat_backend.name, base_url=base_url, api_key=api_key)

    def get_messages(self) -> list[BaseMessage]:
        settings = Settings()

        input_state = self.model_dump()
        system_messages = (
            PromptTemplate.from_template(settings.system_prompt_template, template_format="jinja2")
            .invoke(input=input_state)
            .to_messages()
        )
        return system_messages + self.messages


async def _default_callback(*args, **kwargs):
    return None


def run_sync(state: RedboxState) -> tuple[BaseMessage, timedelta]:
    """
    Run Redbox without streaming events. This simpler, synchronous execution enables use of the graph debug logging
    """
    start = datetime.datetime.now()
    result = state.get_llm().invoke(input=state.get_messages())
    end = datetime.datetime.now()
    return result, end - start


async def run_async(
    state: RedboxState,
    response_tokens_callback=_default_callback,
) -> tuple[AIMessage, timedelta]:
    start = datetime.datetime.now()
    final_message = ""
    async for chunk in state.get_llm().astream(
        state.get_messages(),
    ):
        final_message += chunk.content
        await response_tokens_callback(chunk.content)
    return AIMessage(content=final_message), datetime.datetime.now() - start
```

### Key Changes in the Updated Implementation

1. **Default Model**: Changed from `gpt-4o` to `gemini-2.0-flash`
2. **Default Provider**: Changed from `azure_openai` to `google_genai`
3. **LLM Initialization**: Updated to use `init_chat_model` with provider-specific logic
4. **Streaming**: Updated to use `astream_events` instead of `astream`
5. **Imports**: Added `langchain.chat_models.init_chat_model` and removed `langchain_openai.ChatOpenAI`

## Step 6: Restart Services

### 6.1 Restart Django Container

After updating environment variables, restart the Django container to pick up changes:

```bash
docker compose down django-app
docker compose up -d django-app
```

### 6.2 Verify Configuration

Check that the environment variable is correctly set:

```bash
docker compose exec django-app env | grep GOOGLE_API_KEY
```

Expected output:
```
GOOGLE_API_KEY=your_google_api_key_here
```

## Step 7: Verify Migration

### 7.1 Check Database Configuration

Verify the default backend has been updated:

```bash
docker compose exec django-app venv/bin/django-admin shell -c "from redbox_app.redbox_core.models import ChatLLMBackend; backend = ChatLLMBackend.objects.get(is_default=True); print(f'Default backend: {backend.name} ({backend.provider})')"
```

Expected output:
```
Default backend: gemini-2.0-flash (google_genai)
```

### 7.2 Test Chat Functionality

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
2. **Setting the `GOOGLE_API_KEY` environment variable (MANDATORY)**
3. **Choosing one of four migration methods to update the database configuration**
4. **Updating the `redbox.py` implementation**
5. **Restarting services to pick up changes**

**Important**: The `GOOGLE_API_KEY` environment variable is **REQUIRED** for all migration methods and must be set before proceeding with any database configuration changes.

This approach ensures that the application dynamically uses the database configuration, making it easy to switch between different LLM providers without code changes.
