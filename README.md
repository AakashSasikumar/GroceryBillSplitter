# Instacart Bill Splitter

Manually splitting your Instacart grocery bills when you share groceries with roommates can be annoying. Enter, Instacart Bill Splitter, a tool to help you mostly automate the boring process of splitting Instacart bills.

## Features

- Parse Instacart HTML receipts automatically  
- Interactive CLI for splitting items between people
- Supports multiple people
- Calculates individual shares including common items
- Handles both delivered items and adjustments/refunds

## Development Notes

Type annotations, docstrings, READMEs and other code improvements were added with the assistance of the Continue extension using the Claude 3.5 Sonnet v2 model. While efforts have been made to ensure correctness, any bugs or inconsistencies in these improvements may be attributed to limitations of the LLM and the extension. Please report any issues you find.

## Installation

### Prerequisites

- Python 3.10
- [Poetry](https://python-poetry.org/docs/#installation) package manager

### Steps

1. Clone the repository:

```bash
git clone https://github.com/yourusername/instacart-bill-splitter.git
cd instacart-bill-splitter
```

2. Install dependencies using Poetry:

```bash
poetry install
```

3. Activate the virtual environment:

```bash
poetry env use 3.10
poetry shell
```

## Usage

1. Save your Instacart receipt as HTML:

- Open your Instacart receipt in a web browser
- Save the page as HTML (Ctrl+S or Cmd+S)
- Place the HTML file in the data/receipts/ directory

2. Run the bill splitter:

```python
from pathlib import Path
from billsplitter.extractor import InstacartExtractor
from billsplitter.splitter import BillSplitter

# Load and parse the receipt
bill_data = Path("data/receipts/your-receipt.html").read_text()
extractor = InstacartExtractor(bill_data)
delivered_items = extractor.extract_bill()

# Split the bill
splitter = BillSplitter(
    delivered_items,
    num_people=2,
    people_names=["Person1", "Person2"]
)
split_results = splitter.split_bill()
```

## Interactive Splitting

When running the splitter, you'll be prompted to specify how each item should be split:

- Enter comma-separated numbers to indicate who wants each item (e.g., "1,2" or "12" or "21" means both people share the item)
- Press Enter without input to mark an item as shared by everyone
- Each person is assigned a number (1, 2, etc.)

Example:

```text
Enter the split for each item as comma-separated values:
1.) Bananas x 1 for $3.99: 1
2.) Milk x 1 for $4.99: 1,2
3.) Bread x 1 for $2.99: 2
4.) Cheese x 1 for $5.00: 12
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
