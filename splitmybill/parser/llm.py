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
    MIME_TYPES = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }

    def __init__(
            self,
            image_path: Path,
            model_name: str = "claude-3-5-sonnet-20241022",
            api_key: str | None = None,
            *args,
            **kwargs
    ):
        self.image_path = image_path
        self.image_b64 = self._load_image(image_path)
        self.chat_model = ChatAnthropic(
            model=model_name,
            api_key=api_key
        )
        if kwargs.get("data_model"):
            self.chat_model = self.chat_model.with_structured_output(kwargs.get("data_model"))
        self.chat_model = self.chat_model.with_structured_output(ReceiptModel)

    def extract_bill(self) -> ReceiptModel:
        image_extension = self.image_path.suffix.lower()
        mime_type = self.MIME_TYPES.get(image_extension, 'image/jpeg')

        return self.chat_model.invoke(
            [
                ("system", Constants.SYSTEM_PROMPT),
                HumanMessage(
                    content=[
                        {"type": "text", "text": "Receipt Image:"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{self.image_b64}",
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
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        if image_path.suffix.lower() not in self.MIME_TYPES:
            raise ValueError(
                f"Unsupported image format: {image_path.suffix}. "
                f"Supported formats are: {', '.join(self.MIME_TYPES.keys())}"
            )

        img_base64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        return img_base64
