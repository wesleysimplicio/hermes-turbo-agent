"""
providers.py — provider-agnostic. Does NOT list specific models.

Configure via env (or --model/--base flags):
  SIMPLICIO_MODEL     model id, exactly as the provider expects
                      e.g. "anthropic/claude-opus-4", "openai/gpt-4.1",
                           "z-ai/glm-4.6", "deepseek/deepseek-chat", "any/thing"
  SIMPLICIO_BASE_URL  OpenAI-compatible endpoint
                      OpenRouter: https://openrouter.ai/api/v1
                      GLM:        https://api.z.ai/api/paas/v4
                      local:      http://localhost:11434/v1
  SIMPLICIO_API_KEY   the key (any provider)

Native Anthropic path (no base_url): if SIMPLICIO_BASE_URL is empty AND the
key is ANTHROPIC_API_KEY, the anthropic SDK is used. Otherwise an
OpenAI-compatible client is used pointing at base_url — works for ANY
OpenAI-like provider.
"""
import os

def _cfg():
    return {
        "model": os.environ.get("SIMPLICIO_MODEL"),
        "base":  os.environ.get("SIMPLICIO_BASE_URL"),
        "key":   os.environ.get("SIMPLICIO_API_KEY")
                 or os.environ.get("OPENROUTER_API_KEY")
                 or os.environ.get("ANTHROPIC_API_KEY"),
    }

def _msgs(prompt, feedback):
    m = [{"role": "user", "content": prompt}]
    if feedback:
        m.append({"role": "user",
                  "content": f"The test FAILED:\n{feedback}\nFix it. Same output format."})
    return m

def generate(prompt, feedback=None, max_tokens=4000):
    c = _cfg()
    if not c["model"]:
        raise SystemExit("set SIMPLICIO_MODEL (model id for your provider)")
    if not c["key"]:
        raise SystemExit("set SIMPLICIO_API_KEY (or OPENROUTER_/ANTHROPIC_API_KEY)")

    # native Anthropic path: no base_url
    if not c["base"]:
        import anthropic
        cli = anthropic.Anthropic(api_key=c["key"])
        r = cli.messages.create(model=c["model"], max_tokens=max_tokens,
                                messages=_msgs(prompt, feedback))
        return next((b.text for b in r.content if b.type == "text"), "")

    # any OpenAI-compatible endpoint (OpenRouter, GLM, DeepSeek, local...)
    from openai import OpenAI
    cli = OpenAI(base_url=c["base"], api_key=c["key"])
    r = cli.chat.completions.create(model=c["model"], max_tokens=max_tokens,
                                    messages=_msgs(prompt, feedback))
    return r.choices[0].message.content

def info():
    c = _cfg()
    return (f"model={c['model'] or '(unset)'} "
            f"base={c['base'] or 'anthropic-native'} "
            f"key={'set' if c['key'] else 'MISSING'}")
