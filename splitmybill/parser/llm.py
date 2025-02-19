from __future__ import annotations

import base64
from typing import TYPE_CHECKING, ClassVar

from langchain_core.messages import HumanMessage

from splitmybill.ai_services.llm import LLMProviderFactory
from splitmybill.data_model.receipt import ReceiptModel
from splitmybill.parser.base import BillParserBase

if TYPE_CHECKING:
    from pathlib import Path


class Constants:
    SYSTEM_PROMPT: str = """You are a precise receipt parser that extracts detailed information from
    an image of a receipt. You will be provided a receipt image, and the schema of the desired
    output. Your goal is to extract all relevant information and return an instance of the model.
    """


class AnthropicParser(BillParserBase):
    MIME_TYPES: ClassVar[dict[str, str]] = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp"
    }

    def __init__(
            self,
            image_path: Path,
            model_name: str = "anthropic/claude-3-5-sonnet-20241022",
            api_key: str | None = None,
            **kwargs
    ):
        self.image_path = image_path
        self.image_b64 = self._load_image(image_path)
        self.llm = LLMProviderFactory.create_provider(
            model_name=model_name,
            output_data_model=ReceiptModel,
            api_key=api_key
        )

    def extract_bill(self) -> ReceiptModel:
        image_extension = self.image_path.suffix.lower()
        mime_type = self.MIME_TYPES.get(image_extension, "image/jpeg")

        return self.llm.invoke(
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
    ) -> str:
        if not image_path.exists():
            msg = f"Image file not found: {image_path}"
            raise FileNotFoundError(msg)

        if image_path.suffix.lower() not in self.MIME_TYPES:
            msg = (
                f"Unsupported image format: {image_path.suffix}. "
                f"Supported formats are: {', '.join(self.MIME_TYPES.keys())}"
            )
            raise ValueError(
                msg
            )

        img_base64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        return img_base64
