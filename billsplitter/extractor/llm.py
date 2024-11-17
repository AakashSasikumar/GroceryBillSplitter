from __future__ import annotations

import base64
import json
from io import BytesIO
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from PIL import Image

from billsplitter.data_model.receipt import ReceiptModel
from billsplitter.extractor.base import BillExtractorBase

if TYPE_CHECKING:
    from pathlib import Path


class Constants:
    base_prompt: str = """
    You are an expert at extracting information from receipt images. Please analyze this receipt image and extract a detailed JSON containing all relevant information.

    Focus on extracting:
    - Store/restaurant name
    - Date and time
    - Individual items with:
        - Item name
        - Quantity
        - Unit price
        - Total price
    - Subtotal
    - Taxes
    - Total amount
    - Any discounts or additional fees

    Format the output according to this exact JSON schema:

    {data_model_json}

    Important:
    - Ensure numeric values are parsed as numbers, not strings
    - Maintain exact field names as shown in the schema
    - Include all available fields from the receipt
    - The output must be valid JSON that matches the provided schema
    """


class OllamaVisionExtractor(BillExtractorBase):
    def __init__(
            self,
            image_path: Path,
            model_name: str = "llama3.2-vision:latest",
    ):
        self._data_type = image_path.suffix
        super().__init__(image_path, image_path.suffix)

        self.image_b64 = self._load_image(image_path)
        self.chat_model = ChatOllama(
            model=model_name,
        )
        self.chat_model = self.chat_model.bind(images=[self.image_b64])

    def extract_bill(self) -> ReceiptModel:
        # Get JSON schema from ReceiptModel
        schema = ReceiptModel.model_json_schema()

        # Format prompt with schema
        prompt = Constants.base_prompt.format(
            data_model_json=json.dumps(schema, indent=2)
        )

        # Create message with prompt and image
        message = HumanMessage(
            content=prompt
        )

        # Get response from model
        response = self.chat_model.invoke([message])

        # Extract JSON from response
        try:
            # Find JSON in response by looking for starting '{'
            json_str = response.content[response.content.find("{"):]
            receipt_data = json.loads(json_str)

            # Parse into ReceiptModel
            receipt = ReceiptModel.model_validate(receipt_data)
            return receipt

        except Exception as e:
            raise ValueError(f"Failed to parse LLM response into ReceiptModel: {str(e)}")

    def _load_image(
            self,
            image_path: Path
        ):
        # Open image
        image = Image.open(image_path)

        # Convert RGBA to RGB if needed
        if image.mode == "RGBA":
            # Create white background
            background = Image.new("RGB", image.size, (255, 255, 255))
            # Paste using alpha channel as mask
            background.paste(image, mask=image.split()[3])
            image = background
        elif image.mode != "RGB":
            # Convert any other mode to RGB
            image = image.convert("RGB")

        # Create a BytesIO buffer
        buffered = BytesIO()

        # Save image to buffer in JPEG format with good quality
        image.save(buffered, format="JPEG", quality=95)

        # Get base64 string
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Close buffer
        buffered.close()

        # Return proper base64 format for vision models
        return f"data:image/jpeg;base64,{img_str}"
