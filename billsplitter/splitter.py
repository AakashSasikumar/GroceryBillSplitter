from __future__ import annotations

from prettytable import PrettyTable


class BillSplitterConstants:
    """Constants used in the bill splitting process.

    This class contains various constant values and messages used throughout
    the bill splitting functionality, including CLI instructions and prompts
    for user interaction.

    Attributes:
        cli_instructions: Instructions shown to users for entering item splits.
    """
    cli_instructions = ("\nEnter the split for each item as comma-separated"
                        "values with values indicating which person wants the item."
                        "An empty split string indicates that all people want the item.\n")
    cli_split_string_example = "It can be any combination of the following values: "

    bill_split_total_string = "TOTAL"


class BillSplitter:
    """A class to handle the bill splitting logic and calculations.

    This class manages the process of splitting bills among multiple people,
    handling both common and separate expenses, and calculating individual
    shares of the total bill.

    Args:
        bill_data: The bill data to be split, containing items and their costs.
        num_people: Number of people to split the bill among.
        people_names: List of names of people sharing the bill.
    """
    def __init__(  # noqa: D107, PLR0913, PLR0917
            self,
            bill_data: dict,
            num_people: int,
            people_names: list[str] | None = None,
            smart_split: bool = False,  # noqa: FBT001, FBT002
            historic_data: dict | None = None,
            display_progress_bar: bool = False  # noqa: FBT001, FBT002
        ) -> None:
        self.bill_data = bill_data
        self.num_people = num_people
        self.people_names = people_names
        self.smart_split = smart_split
        self.historic_data = historic_data
        self.display_progress_bar = display_progress_bar

        if not isinstance(self.bill_data, dict):
            msg = "Bill data must be a dictionary"
            raise TypeError(msg)

        if self.people_names and len(self.people_names) != self.num_people:
            msg = "Number of people names must be equal to number of people"
            raise ValueError(msg)

        if self.smart_split:
            msg = "Smart split not implemented yet"
            raise NotImplementedError(msg)

        if self.historic_data:
            msg = "Usage of historic data not implemented yet"
            raise NotImplementedError(msg)

        self._generate_valid_indices()
        if not self.people_names:
            self.people_names = [f"Person {i}" for i in self.valid_indices]

        if self.display_progress_bar:
            msg = "Progress bar not implemented yet"
            raise NotImplementedError(msg)

    def split_bill(
            self,
            display: bool = True  # noqa: FBT001, FBT002
        ) -> dict[str, float]:
        """Split the bill among the specified number of people.

        Processes each item in the bill and calculates individual shares based on
        user input for item splits.

        Args:
            display: If True, displays the splitting process and results in the console.
                    Defaults to True.

        Returns:
            A dictionary mapping each person's name to their total share of the bill.
        """
        bill_common = {}
        bill_separate = self._initialize_bill_split_dictionary()

        if display:
            self._display_split_instructions()
        item_names = list(self.bill_data["items"].keys())
        current_item_index = 0
        while current_item_index < len(item_names):
            item = item_names[current_item_index]
            item_data = self.bill_data["items"][item]
            price = item_data["price"]
            quantity = item_data["quantity"]

            cli_str = self._generate_cli_string(current_item_index + 1, item, quantity, price)
            split_str = input(cli_str)

            if not self._is_valid_split_str(split_str):
                print("Invalid split string. Please enter a valid split string.")  # noqa: T201
                continue

            split_indices = self._extract_split_string_indices(split_str)

            if split_indices == self.valid_indices:
                bill_common[item] = price
            else:
                # If items are separated, then each person gets their own item
                for index in split_indices:
                    person = self.people_names[index - 1]
                    bill_separate[person][item] = round(price / len(split_indices), 5)
            current_item_index += 1

            # TODO: Need to implement progress bar  # noqa: FIX002
            if self.display_progress_bar:
                self.p_bar.update(1)

        bill_common = self._calculate_totals(bill_common, bill_type="common")
        bill_separate = self._calculate_totals(bill_separate, bill_type="separate")
        if display:
            self._display_final_split_data(bill_common, bill_separate)

        return bill_common, bill_separate

    def _calculate_totals(
            self,
            bill_split: tuple[dict[str, float], dict[str, float]],
            bill_type: str = "common"
        ) -> dict[str, float]:
        if bill_type == "common":
            bill_split[BillSplitterConstants.bill_split_total_string] = \
                round(sum(bill_split.values()), 5)
        else:
            for person in self.people_names:
                bill_split[person][BillSplitterConstants.bill_split_total_string] = \
                    round(sum(bill_split[person].values()), 5)
        return bill_split

    def _initialize_bill_split_dictionary(self)  -> dict[str, dict[str, float]]:
        bill_split = {}
        for person in self.people_names:
            bill_split[person] = {}
        return bill_split

    def _extract_split_string_indices(
            self,
            split_str: str,
        ) -> list[int]:
        if split_str == "":  # noqa: PLC1901
            return self.valid_indices

        if "," not in split_str:
            indices = list(split_str)
            if len(indices) == 1:
                return [int(split_str)]
            else:
                return [int(index) for index in indices]
        else:
            return [int(index) for index in split_str.split(",")]

    def _display_split_instructions(self) -> None:
        print(BillSplitterConstants.cli_instructions)  # noqa: T201
        print(BillSplitterConstants.cli_split_string_example, self.valid_indices)  # noqa: T201

    def _generate_cli_string(  # noqa: PLR6301
            self,
            idx: int,
            item: str,
            quantity: int,
            price: float) -> str:
        return f"{idx}.) {item} x {quantity} for ${price}: "

    def _generate_valid_indices(self) -> None:
        self.valid_indices = list(range(1, self.num_people + 1))

    def _is_valid_split_str(
            self,
            split_str: str,
        ) -> bool:
        if split_str == "":  # noqa: PLC1901
            return True

        if "," not in split_str:
            indices = list(split_str)
            if len(indices) == 1:
                index = int(split_str)
                if index in self.valid_indices:
                    return True
            else:
                return all(int(index) in self.valid_indices for index in indices)
        else:
            indices = split_str.split(",")
            return all(int(index) in self.valid_indices for index in indices)
        return None

    def _display_final_split_data(  # noqa: C901
            self,
            common_split: dict[str, float],
            separate_split: dict[str, float],
        ) -> None:
        common_table = PrettyTable()
        separate_table = PrettyTable()
        totals_table = PrettyTable()

        common_table.field_names = ["Common Items", "Price"]
        separate_table.field_names = ["Separate Items", *self.people_names]
        totals_table.field_names = ["Totals", *self.people_names]

        common_rows = []
        separate_rows = []

        person_totals = [0 for _ in range(self.num_people)]

        items = list(self.bill_data["items"].keys())
        items.append(BillSplitterConstants.bill_split_total_string)
        for item in items:
            common_row = [item]
            separate_row = [item]

            if item in common_split:
                common_row.append(common_split[item])
                common_rows.append(common_row)

            for _, person in enumerate(self.people_names):
                if item in separate_split[person]:
                    separate_row.append(separate_split[person][item])
                else:
                    separate_row.append(0)
            separate_rows.append(separate_row)
        common_table.add_rows(common_rows)
        separate_table.add_rows(separate_rows)

        split = \
            round(common_split[BillSplitterConstants.bill_split_total_string] / self.num_people, 5)
        for i in range(self.num_people):
            person_totals[i] += split
        totals_table.add_row(["Common Items"] + [split] * self.num_people)
        separate_total_row = ["Separate Items"]
        for idx, person in enumerate(self.people_names):
            amount = separate_split[person][BillSplitterConstants.bill_split_total_string]
            separate_total_row.append(amount)
            person_totals[idx] += amount
        totals_table.add_row(separate_total_row)

        misc_charges_row = ["Misc. Charges"]
        misc_total = 0
        for key in self.bill_data["order_totals"]:
            if key in {"Items Subtotal", "Total CAD", "Final Total", "You saved"}:
                continue
            misc_total += self.bill_data["order_totals"][key]
        split = round(misc_total / self.num_people, 5)
        for i in range(self.num_people):
            person_totals[i] += split
        misc_charges_row += [split] * self.num_people
        totals_table.add_row(misc_charges_row)
        totals_table.add_row(["TOTAL", *person_totals])

        if round(sum(person_totals), 3) != self.bill_data["order_totals"]["Total CAD"]:
            print("WARNING: The total calculated does not match the total on the bill.")  # noqa: T201
            print(f"Total calculated: {sum(person_totals)}")  # noqa: T201
            print(f"Total on bill: {self.bill_data['order_totals']['Total CAD']}")  # noqa: T201

        print(common_table)  # noqa: T201
        print(separate_table)  # noqa: T201
        print(totals_table)  # noqa: T201
        print("Subtotal: ", sum(person_totals))  # noqa: T201
