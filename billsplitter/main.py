from pathlib import Path

from billsplitter.extractor import InstacartExtractor, OllamaVisionExtractor
from billsplitter.splitter import BillSplitter

test_receipt = Path("data/receipts/images/test_receipt.png")
extractor = OllamaVisionExtractor(image_path=test_receipt)
delivered_items = extractor.extract_bill()
bill_data = Path("data/receipts/Instacart-03-04-2023.html").read_text()

# extractor = InstacartExtractor(bill_data)
# delivered_items = extractor.extract_bill()


# bill_splitter = BillSplitter(delivered_items, num_people=2, people_names=["Subho", "Aakash"])
# bill_splitter.split_bill()

import ollama

response = ollama.chat(
    model='llama3.2-vision',
    messages=[{
        'role': 'user',
        'content': """You are an expert at extracting information from receipt images. Please analyze this receipt image and extract a detailed JSON containing all relevant information.

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

    {
  "$defs": {
    "ItemModel": {
      "description": "Data model representing an individual item in a receipt.",
      "properties": {
        "name": {
          "title": "Name",
          "type": "string"
        },
        "quantity": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "number"
            },
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Quantity"
        },
        "unit_price": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Unit Price"
        },
        "subtotal": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "string"
            }
          ],
          "title": "Subtotal"
        },
        "metadata": {
          "anyOf": [
            {
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Metadata"
        }
      },
      "required": [
        "name",
        "quantity",
        "subtotal"
      ],
      "title": "ItemModel",
      "type": "object"
    },
    "TaxModel": {
      "description": "Data model representing tax and fee items in a receipt.",
      "properties": {
        "name": {
          "title": "Name",
          "type": "string"
        },
        "rate": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Rate"
        },
        "total": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "string"
            }
          ],
          "title": "Total"
        },
        "metadata": {
          "anyOf": [
            {
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Metadata"
        }
      },
      "required": [
        "name",
        "total"
      ],
      "title": "TaxModel",
      "type": "object"
    }
  },
  "description": "Data model representing a receipt structure.\n\nContains lists of items and their associated taxes/fees.",
  "properties": {
    "items": {
      "items": {
        "$ref": "#/$defs/ItemModel"
      },
      "title": "Items",
      "type": "array"
    },
    "taxes_and_fees": {
      "items": {
        "$ref": "#/$defs/TaxModel"
      },
      "title": "Taxes And Fees",
      "type": "array"
    },
    "subtotal": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "string"
        }
      ],
      "title": "Subtotal"
    },
    "metadata": {
      "anyOf": [
        {
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Metadata"
    }
  },
  "required": [
    "items",
    "taxes_and_fees",
    "subtotal"
  ],
  "title": "ReceiptModel",
  "type": "object"
}

    Important:
    - Do not perform any calculations, you are just to read from the image.
    - Ensure numeric values are parsed as numbers, not strings
    - Maintain exact field names as shown in the schema
    - Include all available fields from the receipt
    - The output must be valid JSON that matches the provided schema
    - The output must be a JSON""",
        'images': ['data/receipts/images/test_receipt.png']
    }]
)

print(response)
