# Generated manually to update default backend to Gemini

from django.db import migrations


def update_default_backend_to_gemini(apps, schema_editor):
    """Update the default ChatLLMBackend to use Gemini instead of Azure OpenAI."""
    ChatLLMBackend = apps.get_model("redbox_core", "ChatLLMBackend")
    
    # Find the default backend
    try:
        default_backend = ChatLLMBackend.objects.get(is_default=True)
        # Update it to use Gemini
        default_backend.name = "gemini-2.0-flash"
        default_backend.provider = "google_genai"
        default_backend.description = "Google Gemini 2.0 Flash model"
        default_backend.context_window_size = 128000
        default_backend.save()
        print(f"Updated default backend to: {default_backend.name} ({default_backend.provider})")
    except ChatLLMBackend.DoesNotExist:
        # Create a new Gemini backend if none exists
        ChatLLMBackend.objects.create(
            name="gemini-2.0-flash",
            provider="google_genai",
            description="Google Gemini 2.0 Flash model",
            is_default=True,
            enabled=True,
            context_window_size=128000,
            rate_limit=1000000
        )
        print("Created new Gemini backend as default")


def reverse_update_default_backend_to_gemini(apps, schema_editor):
    """Reverse the migration - set back to Azure OpenAI."""
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
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('redbox_core', '0093_chatmessage_time_to_first_token'),
    ]

    operations = [
        migrations.RunPython(
            update_default_backend_to_gemini,
            reverse_update_default_backend_to_gemini
        ),
    ]
