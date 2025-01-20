from __future__ import annotations

import base64
from typing import TYPE_CHECKING

import pdf2image  # For PDF conversion
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from splitmybill.data_model.receipt import ReceiptModel
from splitmybill.parser.base import BillParserBase

if TYPE_CHECKING:
    from pathlib import Path


class AnthropicParser(BillParserBase):
    SUPPORTED_FORMATS: list = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".pdf"]
    SYSTEM_PROMPT: str = ("You are a program designed to convert images to receipts "
                          "to a JSON according to the JSON Schema")

    def __init__(
            self,
            image_path: Path,
            model_name: str = "claude-3-5-sonnet-20241022",
            api_key: str | None = None,
            *args,
            **kwargs
    ):
        if image_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            msg = f"Unsupported file format. Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            raise ValueError(msg)

        self.file_path = image_path
        self.chat_model = ChatAnthropic(
            model=model_name,
            api_key=api_key
        )
        self.chat_model = self.chat_model.with_structured_output(ReceiptModel)

    def extract_bill(self) -> ReceiptModel:
        content = self._load_file()
        return self.chat_model.invoke(
            [
                ("system", AnthropicParser.SYSTEM_PROMPT),
                HumanMessage(
                    content=[
                        {"type": "text", "text": "Receipt Image:"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": content,
                            },
                        },
                    ]
                )
            ]
        )

    def _load_file(self) -> str:
        """Load and prepare file content for Claude."""
        if self.file_path.suffix.lower() == ".pdf":
            # Convert first page of PDF to image
            images = pdf2image.convert_from_path(self.file_path, first_page=1, last_page=1)
            if not images:
                msg = "Could not extract images from PDF"
                raise ValueError(msg)

            # Save first page temporarily and load it
            temp_path = self.file_path.with_suffix(".png")
            try:
                images[0].save(temp_path)
                img_bytes = Path(temp_path).read_bytes()
            finally:
                temp_path.unlink(missing_ok=True)

            img_base64 = base64.b64encode(img_bytes).decode("utf-8")
            return f"data:image/png;base64,{img_base64}"
        else:
            # Handle regular images
            img_base64 = base64.b64encode(self.file_path.read_bytes()).decode("utf-8")
            mime_type = f"image/{self.file_path.suffix[1:].lower()}"
            return f"data:{mime_type};base64,{img_base64}"
