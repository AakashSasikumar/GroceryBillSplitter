from __future__ import annotations

import logging
from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from tenacity import retry, stop_after_attempt

if TYPE_CHECKING:
    from pydantic import BaseModel

logger = logging.getLogger(__name__)


class BaseLLMProvider():
    def __init__(
            self,
            model_name: str,
            *,
            output_data_model: BaseModel | None = None,
            api_key: str | None = None,
            keep_history: bool = False,
            max_retries: int = 3,
            **kwargs
    ) -> None:
        self.model_name = model_name
        self.output_data_model = output_data_model
        self.keep_history = keep_history
        self.api_key = api_key
        self.history = []

        self.max_retries = max_retries
        self.llm = self._initialize_llm()

    @abstractmethod
    def _initialize_llm(self) -> Any:
        pass

    @abstractmethod
    def _raw_invoke(
        self,
        message: str,
    ) -> Any:
        pass

    def invoke(
            self,
            message: str | list
    ) -> BaseModel | str:
        if self.keep_history:
            self.history.append(
                ("human", message)
            )
            current_message = self.history
        else:
            current_message = message

        try:
            retry_decorator_proxy = retry(stop=stop_after_attempt(self.max_retries))
            response = retry_decorator_proxy(self._raw_invoke)(current_message)
        except Exception as exc:
            logger.exception("Error during LLM invocation")
            msg = "Couldn't get a valid output"
            raise ValueError(msg) from exc
        else:
            if self.keep_history:
                self.history.append(
                    ("assistant", str(response))
                )
            return response
