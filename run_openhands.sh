#!/bin/bash
# =============================================================================
# Launch OpenHands CLI for Milk-V Duo XmrSigner
# =============================================================================

# Export LLM environment variables if using GLM-4 / GLM-5 or OpenAI-compatible endpoint
# export LLM_MODEL="${LLM_MODEL:-glm-5}"
# export LLM_BASE_URL="${LLM_BASE_URL:-https://open.bigmodel.cn/api/paas/v4}"
# export LLM_API_KEY="${LLM_API_KEY:-YOUR_API_KEY}"

cd "$(dirname "$0")"
exec openhands "$@"
