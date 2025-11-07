## Setup

1. Create a free [GitHub Codespace](https://github.com/codespaces/new) from the following repo https://github.com/rubrikinc/agent-cloud-demos
2. In the codespace, make sure you can run the [LiteLLM proxy](https://docs.litellm.ai/docs/proxy/quick_start) with any of the LLM providers that LiteLLM supports. You can use any LLM API provider, most offer a free tier. Alternatively, you can run a local LLM via e.g. ollama, although a model larger than "tinyllama" might be slow to run on the codespace VM. Make sure to use the OpenAI-compatible API with your LLM of choice.
3. In `custom_callbacks.py`, you will find a LiteLLM plugin that blocks access to certain tools. Configure the LiteLLM proxy to load this plugin.