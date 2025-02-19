from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from splitmybill.ai_services.llm.providers.anthropic import AnthropicProvider

if TYPE_CHECKING:
    from pydantic import BaseModel

    from splitmybill.ai_services.llm.base import BaseLLMProvider


class LLMProviderFactory:
    PROVIDER_MAP: ClassVar[dict[str, type[BaseLLMProvider]]] = {
        "anthropic": AnthropicProvider
    }

    @classmethod
    def create_provider(
        cls,
        model_name: str,
        output_data_model: BaseModel | None = None,
        api_key: str | None = None,
        **kwargs
    ) -> BaseLLMProvider:
        """Create an LLM provider based on the model name prefix.

        Args:
            model_name: Model name in format 'provider/model' (e.g., 'anthropic/claude-3')
            output_model: Optional Pydantic model for structured output
            api_key: Optional API key (will try to get from environment if not provided)
            **kwargs: Additional provider-specific arguments

        Returns:
            An initialized LLM provider instance

        Raises:
            ValueError: If provider prefix is not supported or model name format is invalid
        """
        try:
            provider_prefix = model_name.split("/")[0]
        except IndexError as exc:
            err_msg = (
                f"Invalid model name format: {model_name}. "
                "Expected format: '<provider-name/model-name>'",
            )
            raise ValueError(err_msg) from exc

        provider_class = cls.PROVIDER_MAP.get(provider_prefix)
        if not provider_class:
            supported = ", ".join(cls.PROVIDER_MAP.keys())
            err_msg = (
                f"Unsupported provider: {provider_prefix}. "
                f"Supported providers are: {supported}"
            )
            raise ValueError(err_msg)

        return provider_class(
            model_name=model_name,
            output_data_model=output_data_model,
            api_key=api_key,
            **kwargs
        )
