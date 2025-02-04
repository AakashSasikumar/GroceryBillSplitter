from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from langchain_anthropic import ChatAnthropic
from prettytable import PrettyTable

from splitmybill.data_model.split import BillSplitModel, LLMSplitResponse
from splitmybill.interface.base import BaseInterface

if TYPE_CHECKING:
    from splitmybill.data_model.receipt import ItemModel, ReceiptModel


class CLISplitter(BaseInterface):

    SPLIT_INSTRUCTIONS = ("\nEnter the split for each item as comma-separated "
                         "values with values indicating which person wants the item. "
                         "An empty split string indicates that all people want the item.\n")
    SPLIT_EXAMPLE = "It can be any combination of the following values: "
    TOTAL_STRING = "TOTAL"
    TAXES_STRING = "TAXES"
    CURRENCY_SYMBOL = "$"

    def __init__(
            self,
            **kwargs
    ):
        self.participants: list[str] = []
        self.valid_indices: list[int] = []

    def collect_split(
            self,
            receipt_data: ReceiptModel
        ) -> BillSplitModel:
        self.receipt_data = receipt_data
        self._collect_participants()
        self._display_split_instructions()
        return self._process_items(receipt_data)

    def display_split(self, split_data: BillSplitModel) -> None:
        self._display_common_items_table(split_data)
        self._display_separate_items_table(split_data)
        self._display_tax_breakdown_table(split_data)
        self._display_final_totals(split_data)
        self._display_validation_message(split_data)

    def _collect_participants(self) -> None:
        print("\nEnter participant names (empty line to finish):")
        while True:
            name = input("Name: ").strip()
            if not name:
                if len(self.participants) < 2:
                    print("Error: At least 2 participants are required")
                    continue
                break
            if name in self.participants:
                print(f"Error: {name} is already added")
                continue
            self.participants.append(name)

        # Update valid indices after collecting participants
        self.valid_indices = list(range(1, len(self.participants) + 1))

    def _display_split_instructions(self) -> None:
        """Display splitting instructions."""
        print("\nBill Split Instructions:")
        print("-" * 50)
        print(self.SPLIT_INSTRUCTIONS)
        print("Participants:")
        for idx, name in enumerate(self.participants, 1):
            print(f"{idx}. {name}")
        print("\nValid input formats:")
        print("- Empty input (press Enter): Everyone shares the item")
        print("- Single numbers: '1' or '1,2' or '1, 2'")
        print("- Consecutive numbers without commas: '12' means participants 1 and 2")
        print("-" * 50)

    def _process_items(self, receipt_data: ReceiptModel) -> BillSplitModel:
        common_items: list[ItemModel] = []
        separate_items: dict[str, list[ItemModel]] = {
            person: [] for person in self.participants
        }

        for item in receipt_data.items:
            split_indices = self._get_item_split(item)

            if split_indices == self.valid_indices:
                common_items.append(item)
            else:
                share_amount = item.subtotal / len(split_indices)
                for idx in split_indices:
                    person = self.participants[idx - 1]
                    # TODO: Figure out a more memory efficient way
                    item_share = item.model_copy(update={"subtotal": share_amount})
                    separate_items[person].append(item_share)
        split_data = BillSplitModel(
            common_items=common_items,
            separate_items=separate_items,
            participants=self.participants
        )
        split_data.calculate_shares(receipt_data)
        return split_data

    def _get_item_split(self, item: ItemModel) -> list[int]:
        """Get and validate split information for an item."""
        while True:
            prompt = self._format_item_prompt(item)
            split_str = input(prompt)

            if self._is_valid_split_str(split_str):
                return self._extract_split_string_indices(split_str)

            print("\nError: Invalid split format")
            self._display_split_format_help()

    def _format_item_prompt(self, item: ItemModel) -> str:
        """Format the prompt string for an item."""
        parts = [item.name]

        if item.quantity is not None:
            parts.append(f"x {item.quantity}")

        if item.unit_price is not None:
            parts.append(f"@ {self.CURRENCY_SYMBOL}{item.unit_price:.2f}")

        parts.append(f"(Total: {self.CURRENCY_SYMBOL}{item.subtotal:.2f})")
        return " ".join(parts) + ": "

    def _display_common_items_table(self, split_model: BillSplitModel) -> None:
        """Display table of common items."""
        if not split_model.common_items:
            print("\nNo common items")
            return

        table = PrettyTable()
        table.field_names = ["Common Items", "Price", "Per Person"]
        per_person = len(split_model.participants)

        for item in split_model.common_items:
            table.add_row([
                item.name,
                f"{self.CURRENCY_SYMBOL}{item.subtotal:.2f}",
                f"{self.CURRENCY_SYMBOL}{(item.subtotal / per_person):.2f}"
            ])

        print("\nCOMMON ITEMS:")
        print(table)

    def _display_separate_items_table(self, split_model: BillSplitModel) -> None:
        """Display table of separately split items."""
        if not split_model.separate_items:
            return
        if not any(split_model.separate_items.values()):
            print("\nNo separate items")
            return

        table = PrettyTable()
        table.field_names = ["Separate Items", *self.participants]

        # Get all unique items
        all_items = set()
        for items in split_model.separate_items.values():
            all_items.update(item.name for item in items)

        # Create rows
        for item_name in sorted(all_items):
            row = [item_name]
            for person in self.participants:
                amount = sum(
                    item.subtotal  # subtotal is already the share
                    for item in split_model.separate_items.get(person, [])
                    if item.name == item_name
                )
                row.append(f"{self.CURRENCY_SYMBOL}{amount:.2f}")
            table.add_row(row)

        print("\nSEPARATE ITEMS:")
        print(table)

    def _display_tax_breakdown_table(self, split_model: BillSplitModel) -> None:
        """Display tax breakdown table."""
        table = PrettyTable()
        table.field_names = ["Person", "Pretax Amount", "Tax Share", "Total"]

        # Add row for each person
        for person in self.participants:
            table.add_row([
                person,
                f"{self.CURRENCY_SYMBOL}{split_model.participant_shares[person]:.2f}",
                f"{self.CURRENCY_SYMBOL}{split_model.tax_shares[person]:.2f}",
                f"{self.CURRENCY_SYMBOL}{split_model.total_shares[person]:.2f}"
            ])

        # Add total row
        total_pretax = sum(split_model.participant_shares.values())
        total_tax = sum(split_model.tax_shares.values())
        total_final = sum(split_model.total_shares.values())

        table.add_row([
            "TOTAL",
            f"{self.CURRENCY_SYMBOL}{total_pretax:.2f}",
            f"{self.CURRENCY_SYMBOL}{total_tax:.2f}",
            f"{self.CURRENCY_SYMBOL}{total_final:.2f}"
        ])

        print("\nTAX BREAKDOWN:")
        print(table)

    def _display_final_totals(self, split_model: BillSplitModel) -> None:
        """Display final amount owed by each person."""
        print("\nFINAL TOTALS:")
        for person in self.participants:
            total = split_model.total_shares[person]
            print(f"{person}: {self.CURRENCY_SYMBOL}{total:.2f}")

    def _display_validation_message(self, split_model: BillSplitModel) -> None:
        """Display validation message comparing against receipt total."""
        total_bill = sum(split_model.total_shares.values())

        if abs(total_bill - self.receipt_data.total) > Decimal("0.01"):
            print("\nWARNING: Total bill amount differs from receipt total")
            print(f"Calculated total: {self.CURRENCY_SYMBOL}{total_bill:.2f}")
            print(f"Receipt total: {self.CURRENCY_SYMBOL}{self.receipt_data.total:.2f}")

    def _is_valid_split_str(self, split_str: str) -> bool:
        """Validate the split string format."""
        if split_str == "":
            return True

        try:
            indices = self._extract_split_string_indices(split_str)
            return bool(indices) and all(idx in self.valid_indices for idx in indices)
        except ValueError:
            return False

    def _extract_split_string_indices(self, split_str: str) -> list[int]:
        """Extract participant indices from the split string."""
        if split_str == "":
            return self.valid_indices

        # Handle both comma-separated and non-comma-separated inputs
        if "," in split_str:
            parts = [p.strip() for p in split_str.split(",")]
        else:
            parts = list(split_str.replace(" ", ""))

        try:
            indices = [int(part) for part in parts if part]
            return sorted(set(indices))  # Remove duplicates and sort
        except ValueError as e:
            raise ValueError("Invalid split string format") from e

    def _display_split_format_help(self) -> None:
        """Display help message for split format."""
        print("\nPlease enter:")
        print("- Nothing (press Enter) if everyone shares the item")
        print("- Numbers corresponding to participants (e.g., '1,2' or '12')")
        print(f"- Valid participant numbers are: {self.valid_indices}\n")


class SmartCLISplitter(BaseInterface):
    """A smart CLI interface that uses natural language processing to split bills."""

    CURRENCY_SYMBOL = "$"

    SPLIT_INSTRUCTIONS = """
Please describe how you want to split the bill. You can use natural language.
For example:
    - "Split everything equally between all participants"
    - "Alice and Bob share the pizza, everyone splits the appetizers"
    - "The coffee is just for Charlie, split everything else equally"

Enter your splitting instructions:"""

    SYSTEM_PROMPT = """You are an AI assistant that helps split bills between people.

Your task is:
1. Review the receipt items and participant list provided
2. Understand the natural language splitting instructions
3. Create a BillSplitModel with:
   - Common items (split equally among all participants)
   - Separate items (split between specific participants)
4. If any items aren't clearly addressed in the instructions, ask for clarification

Rules for splitting:
- Items must be either common (everyone) or separate (specific people)
- For separate items:
  * Create duplicate items for each participant sharing the item
  * Split the cost equally between participants
  * Example: A $20 pizza split between Alice and Bob creates:
    - Pizza (Alice's share) at $10
    - Pizza (Bob's share) at $10
- All items must be accounted for in the final split
- All splits must be mathematically correct and total to the receipt amount

Remember:
- Ask for clarification if any item's split is unclear
- Return a complete response only when all items have clear split instructions
- Maintain context from previous clarifications in the conversation"""

    def __init__(
            self,
            model_name: str = "claude-3-5-sonnet-20241022",
            api_key: str | None = None,
            **kwargs
    ):
        self.participants: list[str] = []
        self.chat_model = ChatAnthropic(
            model=model_name,
            api_key=api_key
        ).with_structured_output(LLMSplitResponse)
        self.chat_history: List[Tuple[str, Any]] = []
        self.receipt_data: ReceiptModel | None = None

    def collect_split(
            self,
            receipt_data: ReceiptModel
        ) -> BillSplitModel:
        self.receipt_data = receipt_data
        self._collect_participants()
        self._initialize_chat_history()

        print(self.SPLIT_INSTRUCTIONS)
        
        while True:
            instructions = input("> ").strip()
            response = self._process_instructions(instructions)

            if response.is_complete:
                split_result = response.split_result
                split_result.calculate_shares(receipt_data)
                return split_result

            print(f"\n{response.clarification_question}")

    def _collect_participants(self) -> None:
        print("\nEnter participant names (empty line to finish):")
        while True:
            name = input("Name: ").strip()
            if not name:
                if len(self.participants) < 2:
                    print("Error: At least 2 participants are required")
                    continue
                break
            if name in self.participants:
                print(f"Error: {name} is already added")
                continue
            self.participants.append(name)

    def _initialize_chat_history(self) -> None:
        self.chat_history = [
            ("system", self.SYSTEM_PROMPT),
            ("human", (
                "Here is the receipt and participant information:\n"
                f"Receipt: {self.receipt_data.model_dump()}\n"
                f"Participants: {self.participants}"
            ))
        ]

    def _process_instructions(self, instructions: str) -> LLMSplitResponse:
        self.chat_history.append(
            ("human", instructions)
        )

        response: LLMSplitResponse = self.chat_model.invoke(self.chat_history)

        self.chat_history.append(
            ("assistant", str(response.model_dump()))
        )

        return response

    def display_split(self, split_data: BillSplitModel) -> None:
        self._display_common_items_table(split_data)
        self._display_separate_items_table(split_data)
        self._display_tax_breakdown_table(split_data)
        self._display_final_totals(split_data)
        self._display_validation_message(split_data)

    def _display_common_items_table(self, split_model: BillSplitModel) -> None:
        if not split_model.common_items:
            print("\nNo common items")
            return

        table = PrettyTable()
        table.field_names = ["Common Items", "Price", "Per Person"]
        per_person = len(split_model.participants)

        for item in split_model.common_items:
            table.add_row([
                item.name,
                f"{self.CURRENCY_SYMBOL}{item.subtotal:.2f}",
                f"{self.CURRENCY_SYMBOL}{(item.subtotal / per_person):.2f}"
            ])

        print("\nCOMMON ITEMS:")
        print(table)

    def _display_separate_items_table(self, split_model: BillSplitModel) -> None:
        if not split_model.separate_items:
            return
        if not any(split_model.separate_items.values()):
            print("\nNo separate items")
            return

        table = PrettyTable()
        table.field_names = ["Separate Items", *self.participants]

        all_items = set()
        for items in split_model.separate_items.values():
            all_items.update(item.name for item in items)

        for item_name in sorted(all_items):
            row = [item_name]
            for person in self.participants:
                amount = sum(
                    item.subtotal
                    for item in split_model.separate_items.get(person, [])
                    if item.name == item_name
                )
                row.append(f"{self.CURRENCY_SYMBOL}{amount:.2f}")
            table.add_row(row)

        print("\nSEPARATE ITEMS:")
        print(table)

    def _display_tax_breakdown_table(self, split_model: BillSplitModel) -> None:
        table = PrettyTable()
        table.field_names = ["Person", "Pretax Amount", "Tax Share", "Total"]

        for person in self.participants:
            table.add_row([
                person,
                f"{self.CURRENCY_SYMBOL}{split_model.participant_shares[person]:.2f}",
                f"{self.CURRENCY_SYMBOL}{split_model.tax_shares[person]:.2f}",
                f"{self.CURRENCY_SYMBOL}{split_model.total_shares[person]:.2f}"
            ])

        total_pretax = sum(split_model.participant_shares.values())
        total_tax = sum(split_model.tax_shares.values())
        total_final = sum(split_model.total_shares.values())

        table.add_row([
            "TOTAL",
            f"{self.CURRENCY_SYMBOL}{total_pretax:.2f}",
            f"{self.CURRENCY_SYMBOL}{total_tax:.2f}",
            f"{self.CURRENCY_SYMBOL}{total_final:.2f}"
        ])

        print("\nTAX BREAKDOWN:")
        print(table)

    def _display_final_totals(self, split_model: BillSplitModel) -> None:
        print("\nFINAL TOTALS:")
        for person in self.participants:
            total = split_model.total_shares[person]
            print(f"{person}: {self.CURRENCY_SYMBOL}{total:.2f}")

    def _display_validation_message(self, split_model: BillSplitModel) -> None:
        total_bill = sum(split_model.total_shares.values())

        if abs(total_bill - self.receipt_data.total) > Decimal("0.01"):
            print("\nWARNING: Total bill amount differs from receipt total")
            print(f"Calculated total: {self.CURRENCY_SYMBOL}{total_bill:.2f}")
            print(f"Receipt total: {self.CURRENCY_SYMBOL}{self.receipt_data.total:.2f}")