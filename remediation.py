"""AI remediation via a pluggable LLM adapter. Output is always labelled and evidence-linked."""
from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod

from .models import DISCLAIMER, Finding

SYSTEM = (
    "You are an accessibility engineer. Given ONE automated finding, return ONLY compact JSON with keys "
    "user_impact (1-2 sentences, who is affected and how), suggested_fix (1-3 sentences), "
    "sample_markup (corrected HTML for the given snippet). Do not claim WCAG compliance. "
    "If unsure, say so in suggested_fix. No markdown fences."
)


class LLMAdapter(ABC):
    name = "base"

    @abstractmethod
    def complete(self, system: str, prompt: str) -> str: ...


class AnthropicAdapter(LLMAdapter):
    def __init__(self, model: str):
        import anthropic  # lazy import
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self.client = anthropic.Anthropic(api_key=key)
        self.model = model
        self.name = f"anthropic:{model}"

    def complete(self, system: str, prompt: str) -> str:
        msg = self.client.messages.create(
            model=self.model, max_tokens=600, system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


def build_adapter(provider: str, model: str) -> LLMAdapter | None:
    if provider == "anthropic":
        return AnthropicAdapter(model)
    return None


def _base(f: Finding, rules: dict) -> dict:
    r = rules.get(f.rule_id)
    if r:
        return {"user_impact": r["user_impact"], "suggested_fix": r["fix"], "sample_markup": r["sample"],
                "ai_generated": False, "origin": "rule knowledge base"}
    return {"user_impact": "See the linked rule documentation for who is affected.",
            "suggested_fix": f.message, "sample_markup": "", "ai_generated": False,
            "origin": f"axe-core rule documentation ({f.help_url})" if f.help_url else "axe-core"}


def remediate(f: Finding, rules: dict, adapter: LLMAdapter | None) -> dict:
    out = _base(f, rules)
    out["evidence"] = {"selector": f.selector, "html": f.html, "message": f.message}
    out["disclaimer"] = DISCLAIMER
    if adapter is None:
        return out
    prompt = (f"Rule: {f.rule_id} (WCAG {f.wcag})\nProblem: {f.message}\nSelector: {f.selector}\n"
              f"HTML: {f.html}\nSurrounding text: {f.context}")
    try:
        raw = adapter.complete(SYSTEM, prompt)
        data = json.loads(re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip())
        for k in ("user_impact", "suggested_fix", "sample_markup"):
            if isinstance(data.get(k), str) and data[k].strip():
                out[k] = data[k].strip()
        out.update(ai_generated=True, origin=f"AI ({adapter.name}); verify before applying",
                   confidence_note="AI suggestion – may be wrong for your context.")
    except Exception as e:  # network, quota, bad JSON: degrade gracefully
        out["ai_error"] = f"AI unavailable ({type(e).__name__}); showing rule-based guidance."
    return out
