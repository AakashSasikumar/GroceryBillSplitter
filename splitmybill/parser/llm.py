from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from splitmybill.data_model.receipt import ReceiptModel
from splitmybill.parser.base import BillParserBase

if TYPE_CHECKING:
    from pathlib import Path


class Constants:
    SYSTEM_PROMPT: str = ("You are a program designed to convert images to receipts "
                          "to a JSON according to the JSON Schema")


class AnthropicParser(BillParserBase):
    def __init__(
            self,
            image_path: Path,
            model_name: str = "claude-3-5-sonnet-20241022",
            api_key: str | None = None,
            *args,
            **kwargs
    ):
        self.image_b64 = self._load_image(image_path)
        self.chat_model = ChatAnthropic(
            model=model_name,
            api_key=api_key
        )
        self.chat_model = self.chat_model.with_structured_output(ReceiptModel)

    def extract_bill(self) -> ReceiptModel:
        return self.chat_model.invoke(
            [
                ("system", Constants.SYSTEM_PROMPT),
                HumanMessage(
                    content=[
                        {"type": "text", "text": "Receipt Image:"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{self.image_b64}",
                            },
                        },
                    ]
                )
            ]
        )

    def _load_image(
            self,
            image_path: Path
        ):
        # Open image
        img_base64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        return img_base64
