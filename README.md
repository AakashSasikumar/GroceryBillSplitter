# Split My Bill (`splitmybill`)

A tool born out of sheer laziness. Presenting to you ... `splitmybill`: the ultimate grocery bill splitting tool.

Say goodbye to sitting down with a pen and paper to figure out how to split your shared grocery receipt with your roommates.

## Features

- **Multi-format Receipt Support**:
  - Parse Instacart HTML receipts with item details, prices, and quantities
  - Extract information from receipt images (PNG, JPEG, etc.)
- **Interactive CLI**:
  - User-friendly interface for splitting items
  - Supports splitting a bill with up to 9 people
  - Flexible item attribution between any combination of people
- **Detailed Reports**: Generate comprehensive split summaries

## Quick Start

```bash
# Install the tool
pip install git+https://github.com/AakashSasikumar/GroceryBillSplitter.git

# Split an image receipt (requires Anthropic API key)
splitmybill receipt.png --anthropic-key your-key-here
# OR use environment variable
export ANTHROPIC_API_KEY=your-key-here
splitmybill receipt.png
```

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Interactive Splitting](#interactive-splitting)
- [Road Map](#road-map)
- [License](#license)
- [Customization](#customization)

## Installation

You will need Python 3.10 or higher to use this tool.

### For Users

1. Install it using pip

```bash
pip install git+https://github.com/AakashSasikumar/GroceryBillSplitter.git
```

### For Developers

1. Clone the repository:

```bash
git clone https://github.com/AakashSasikumar/GroceryBillSplitter.git
cd grocery-bill-splitter
```

2. [Install Poetry](https://python-poetry.org/docs/)

3. Set up the development environment

```bash
poetry env use 3.10
poetry shell
```

4. Install the CLI tool

```bash
poetry install
```

## Usage

### As a CLI Tool

```bash
# Basic usage
splitmybill /path/to/receipt.[html|png|jpg]
```

For parsing receipt images (PNG, JPEG, etc.), `splitmybill` uses Claude's multimodal capabilities through the Anthropic API. You'll need an API key to use this feature:

1. Get your Anthropic API key from [https://console.anthropic.com/](https://console.anthropic.com/)
2. Provide it in one of two ways:
   ```bash
   # Option 1: Command line argument
   splitmybill receipt.png --anthropic-key your-key-here

   # Option 2: Environment variable
   export ANTHROPIC_API_KEY=your-key-here
   splitmybill receipt.png
   ```

Note: HTML receipts from Instacart don't require an API key.
### Interactive Splitting

The CLI provides a user-friendly interactive interface for splitting bills. Here's a walkthrough of the process:

1. First, you'll be prompted to enter participant names:
```text
Enter participant names (empty line to finish):
Name: Alice
Name: Bob
Name: Charlie
Name: 
```

2. You'll see the splitting instructions:
```text
Bill Split Instructions:
--------------------------------------------------
Enter the split for each item as comma-separated values with values indicating which person wants the item.
An empty split string indicates that all people want the item.

Participants:
1. Alice
2. Bob
3. Charlie

Valid input formats:
- Empty input (press Enter): Everyone shares the item
- Single numbers: '1' or '1,2' or '1, 2'
- Consecutive numbers without commas: '12' means participants 1 and 2
--------------------------------------------------
```

3. For each item, you'll be shown details and prompted for splitting:
```text
Bananas x 2 @ $0.99 (Total: $1.98): 1
Milk x 1 @ $4.99 (Total: $4.99): 
Pizza x 1 @ $15.99 (Total: $15.99): 2,3
Ice Cream x 2 @ $5.99 (Total: $11.98): 23
```

4. After all items are processed, you'll see multiple summary tables:

Common Items (shared by everyone):
```text
COMMON ITEMS:
+------+-------+------------+
| Item | Price | Per Person |
+------+-------+------------+
| Milk | $4.99 |    $1.66  |
+------+-------+------------+
```

Separate Items:
```text
SEPARATE ITEMS:
+------------+---------+--------+-----------+
| Item       | Alice   | Bob    | Charlie   |
+------------+---------+--------+-----------+
| Bananas    | $1.98   | $0.00  | $0.00    |
| Pizza      | $0.00   | $8.00  | $8.00    |
| Ice Cream  | $0.00   | $5.99  | $5.99    |
+------------+---------+--------+-----------+
```

Tax Breakdown:
```text
TAX BREAKDOWN:
+----------+---------------+-----------+---------+
| Person   | Pretax Amount | Tax Share | Total  |
+----------+---------------+-----------+---------+
| Alice    | $3.64        | $0.29     | $3.93  |
| Bob      | $15.65       | $1.25     | $16.90 |
| Charlie  | $15.65       | $1.25     | $16.90 |
| TOTAL    | $34.94       | $2.79     | $37.73 |
+----------+---------------+-----------+---------+
```

Final Totals:
```text
FINAL TOTALS:
Alice: $3.93
Bob: $16.90
Charlie: $16.90
```

- NOTE: This method can only work for up to 9 people. Write your own Splitter class if you want to extend it.

## Road Map

- Mobile interface via some chatbot
  - Maybe a Telegram bot?
- Integration with Splitwise
- Explaining how the bill was split through natural language

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

---

## Customization

`splitmybill` is pretty customizable. There are three core components:

1. Parsers:
Parsers convert different receipt formats to a standardized data model:

- `InstacartParser`: Parses Instacart HTML Receipts
- `AnthropicParser`: Uses Claude's multimodality to parse a receipt image
- Create your own by extending the `BaseExtractor` class

```python
from splitmybill.parser.base import BillParserBase

class MyCustomExtractor(BaseExtractor):
    def extract_bill(self) -> ReceiptModel:
        # Your parsing logic here
        return ReceiptModel(...)
```

2. Data Models
Standardized models representing the receipt, split information, etc

- `ReceiptModel`: Contains basically the whole receipt
- `BillSplitModel`: Holds the final split calculations

3. Interface
Handles the interaction and logic of dividing items between people

- `CLIInterface`: Default implementation
- Create custom interfaces for different platforms

```python
from splitmybill.interface.base import BaseInterface

class CustomInterface(BaseInterface):
    def collect_split(self, receipt_data: ReceiptModel) -> BillSplitModel:
        # Your splitting logic here
        return BillSplitModel(...)
    
    def display_split(self, split_data: BillSplitModel) -> None:
        # Your display logic here
        pass
```
