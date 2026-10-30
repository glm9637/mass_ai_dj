"""Constants for the AI DJ integration."""

DOMAIN = "mass_ai_dj"

CONF_PROVIDER = "provider"
CONF_GEMINI_API_KEY = "gemini_api_key"
CONF_GEMINI_MODEL = "gemini_model"
CONF_OLLAMA_URL = "ollama_url"
CONF_OLLAMA_MODEL = "ollama_model"

PROVIDER_GEMINI = "Gemini (Cloud)"
PROVIDER_OLLAMA = "Ollama (Local)"

# Alias for the current Flash-Lite model: answers in ~1s. The full Flash alias
# (gemini-flash-latest) took over 100s per request on the free tier.
DEFAULT_GEMINI_MODEL = "gemini-flash-lite-latest"