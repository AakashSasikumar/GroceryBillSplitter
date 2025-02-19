from __future__ import annotations

from langchain_anthropic import ChatAnthropic

from splitmybill.ai_services.llm.base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
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
    ):
        return self.llm.invoke(message)
