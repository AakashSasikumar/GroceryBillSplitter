from __future__ import annotations

from langchain_anthropic import ChatAnthropic

from splitmybill.ai_services.llm.base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    """Anthropic LLM provider implementation using Claude models.

    This class implements the BaseLLMProvider interface for Anthropic's Claude
    models, handling initialization and interaction with the Anthropic API.

    Attributes:
        model_name (str): Name of the Anthropic model to use
        api_key (str): Anthropic API key for authentication
    """
    def _initialize_llm(self) -> ChatAnthropic:
        llm = ChatAnthropic(
            model=self.model_name.split("/", 1)[1],
            api_key=self.api_key
        )

        if self.output_data_model:
            llm = llm.with_structured_output(
                self.output_data_model
            )
        return llm

    def _raw_invoke(
            self,
            message: str | list
    ) -> str | dict:
        return self.llm.invoke(message)
