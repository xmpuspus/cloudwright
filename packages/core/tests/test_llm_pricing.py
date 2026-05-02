"""Per-model pricing tests for AnthropicLLM and OpenAILLM.

Pre-fix bug: ``llm.pricing`` was a single dict at the Sonnet rate, so Haiku
calls were billed at 4x the real price (Haiku = $0.0008 input vs Sonnet =
$0.003 input). After the fix, pricing is keyed by model name and the
session looks up the rate via the ``model`` field returned in the usage dict.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from cloudwright.architect import ConversationSession
from cloudwright.llm.anthropic import _HAIKU_PRICING, _SONNET_PRICING, AnthropicLLM
from cloudwright.llm.openai import _GPT5_MINI_PRICING, _GPT5_PRICING, OpenAILLM


class TestAnthropicPricingTable:
    def test_haiku_model_gets_haiku_rates(self):
        llm = AnthropicLLM(api_key="test")
        rate = llm.pricing_for("claude-haiku-4-5-20251001")
        assert rate == _HAIKU_PRICING

    def test_haiku_prefix_match(self):
        llm = AnthropicLLM(api_key="test")
        # The dated suffix shouldn't break the lookup.
        rate = llm.pricing_for("claude-haiku-4-5-20260101")
        assert rate == _HAIKU_PRICING

    def test_sonnet_model_gets_sonnet_rates(self):
        llm = AnthropicLLM(api_key="test")
        assert llm.pricing_for("claude-sonnet-4-6") == _SONNET_PRICING

    def test_unknown_model_falls_back_to_default(self):
        llm = AnthropicLLM(api_key="test")
        # Unknown model defaults to Sonnet — safer to over-bill than silently
        # bill 10x wrong like the pre-fix Haiku case.
        assert llm.pricing_for("claude-mystery-99") == _SONNET_PRICING

    def test_none_model_defaults(self):
        llm = AnthropicLLM(api_key="test")
        assert llm.pricing_for(None) == _SONNET_PRICING

    def test_legacy_pricing_property_returns_default(self):
        # Older callers still read llm.pricing — must keep working.
        llm = AnthropicLLM(api_key="test")
        assert llm.pricing == _SONNET_PRICING


class TestOpenAIPricingTable:
    def test_gpt5_mini_gets_mini_rates(self):
        llm = OpenAILLM(api_key="test")
        assert llm.pricing_for("gpt-5-mini") == _GPT5_MINI_PRICING

    def test_gpt5_gets_gpt5_rates(self):
        llm = OpenAILLM(api_key="test")
        assert llm.pricing_for("gpt-5.2") == _GPT5_PRICING
        assert llm.pricing_for("gpt-5") == _GPT5_PRICING

    def test_unknown_model_falls_back(self):
        llm = OpenAILLM(api_key="test")
        assert llm.pricing_for("gpt-3.5-mystery") == _GPT5_PRICING

    def test_mini_prefix_does_not_match_full_gpt5(self):
        # Prefix-match ordering must check the more-specific "mini" first.
        llm = OpenAILLM(api_key="test")
        assert llm.pricing_for("gpt-5-mini-2024") == _GPT5_MINI_PRICING
        assert llm.pricing_for("gpt-5-2024") == _GPT5_PRICING


class TestUsageReturnsModel:
    """The provider must return the model id in the usage dict so the session
    bills against the correct rate."""

    def test_anthropic_call_returns_model(self):
        llm = AnthropicLLM(api_key="test")
        llm.client = MagicMock()
        response = MagicMock()
        response.content = [MagicMock(text="ok")]
        response.usage.input_tokens = 10
        response.usage.output_tokens = 5
        response.usage.cache_read_input_tokens = 0
        response.usage.cache_creation_input_tokens = 0
        llm.client.messages.create.return_value = response

        # Generate (Sonnet) and generate_fast (Haiku) must each report the
        # right model so cost lookup downstream is accurate.
        _, sonnet_usage = llm.generate([{"role": "user", "content": "hi"}], "system")
        _, haiku_usage = llm.generate_fast([{"role": "user", "content": "hi"}], "system")

        assert sonnet_usage["model"].startswith("claude-sonnet")
        assert haiku_usage["model"].startswith("claude-haiku")

    def test_openai_call_returns_model(self):
        llm = OpenAILLM(api_key="test")
        llm.client = MagicMock()
        response = MagicMock()
        response.choices = [MagicMock(message=MagicMock(content="ok"))]
        response.usage.prompt_tokens = 10
        response.usage.completion_tokens = 5
        response.usage.prompt_tokens_details = MagicMock(cached_tokens=3)
        llm.client.chat.completions.create.return_value = response

        _, usage = llm.generate([{"role": "user", "content": "hi"}], "system")
        assert usage["model"].startswith("gpt-5")
        assert usage["cached_tokens"] == 3


class TestSessionBillsAtCorrectRate:
    """The session must bill Haiku-routed calls at Haiku rates, not Sonnet."""

    def _mock_llm(self, model: str, rate: dict):
        llm = MagicMock()
        llm.model_name = model
        llm.pricing_for = lambda m=None: rate
        # Old API still readable.
        llm.pricing = rate
        llm.estimate_tokens = lambda t: max(1, len(t) // 4)
        return llm

    def test_session_uses_pricing_for_with_model_from_usage(self):
        llm = self._mock_llm("claude-sonnet-4-6", _SONNET_PRICING)
        # Override pricing_for to verify it's called with the model name.
        called_with: list[str | None] = []

        def fake_pricing(model=None):
            called_with.append(model)
            return _HAIKU_PRICING if model and "haiku" in model else _SONNET_PRICING

        llm.pricing_for = fake_pricing
        llm.generate.return_value = (
            "no spec here",
            {"model": "claude-haiku-4-5-20251001", "input_tokens": 1000, "output_tokens": 1000},
        )

        session = ConversationSession(llm=llm)
        session.send("design a web app on aws")

        assert "claude-haiku-4-5-20251001" in called_with
        # 1000 input * 0.0008/1000 + 1000 output * 0.004/1000 = 0.0008 + 0.004 = 0.0048
        assert session.last_usage["estimated_cost"] == 0.0048
        assert session.last_usage["cost_usd"] == 0.0048

    def test_session_falls_back_when_no_model_in_usage(self):
        # Older usage dicts (no model field) still work — bill at default rate.
        llm = self._mock_llm("claude-sonnet-4-6", _SONNET_PRICING)
        llm.generate.return_value = ("text", {"input_tokens": 1000, "output_tokens": 1000})
        session = ConversationSession(llm=llm)
        session.send("design web app on aws")
        # Sonnet rate: 1000 * 0.003/1000 + 1000 * 0.015/1000 = 0.003 + 0.015 = 0.018
        assert session.last_usage["estimated_cost"] == 0.018
