from __future__ import annotations

from typing import ClassVar

from bs4 import BeautifulSoup

from billsplitter.extractor import BillExtractorBase


class InstacartHTMLConstants:
    """Constants for parsing Instacart HTML receipt tables.

    This class contains the HTML class names used to identify and extract
    information from Instacart receipt tables.

    Attributes:
        adjusted_items_table_class: HTML class for the adjustments items table.
        found_items_table_class: HTML class for the delivered items table.
    """
    adjusted_items_table_class = "items adjustments"
    found_items_table_class = "items delivered"

    items_block_class = ".item-block"
    items_wanted_class = ".item-wanted .item-name"
    items_delivered_class = ".item-delivered .item-name"
    items_delivered_price_class = ".item-delivered .total"

    items_name_class = ".item-name"
    item_quantity_class = ".item-name .muted"
    items_price_class = ".item-price .total"

    charges_table_class = "charges"
    charge_type_class = ".charge-type"
    charge_amount_class = ".amount"
    charge_final_name = "Total CAD"

    ignore_keys: ClassVar[list[str]] = ["Instacart+ Member Free Delivery!"]


class InstacartExtractor(BillExtractorBase):
    """Extractor for parsing Instacart HTML receipts.

    This class implements the bill extraction logic specifically for Instacart
    receipts in HTML format. It parses the HTML structure to extract items,
    prices, and other relevant billing information.

    Args:
        bill_data: Raw HTML content of the Instacart receipt.
        bill_type: Format of the bill, defaults to "html".
    """
    def __init__(
            self,
            bill_data: str,
            bill_type: str = "html",
    ) -> None:
        """Initialize the Instacart receipt extractor.

        Args:
            bill_data: Raw HTML content of the Instacart receipt to be parsed.
            bill_type: Format of the bill data, defaults to "html".
        """
        super().__init__(bill_data, bill_type)

        self._make_soup()

    def extract_bill(self)  -> dict[str, list[dict[str, str | float]] | dict[str, float]]:
        """Extract all relevant information from the Instacart receipt.

        Processes the HTML receipt to extract adjusted items, found items, and order totals.

        Returns:
            A dictionary containing:
                - 'adjusted_items': List of items that were adjusted (refunded/modified)
                - 'found_items': List of items that were actually delivered
                - 'order_totals': Dictionary of various total amounts in the order

            Each item in the lists is a dictionary containing item details like
            name, price, and quantity.
        """
        adjusted_items = self._extract_adjusted_items()
        found_items = self._extract_found_items()
        order_totals = self._extract_order_totals()

        all_items = {}
        all_items["items"] = {**adjusted_items, **found_items}
        all_items["order_totals"] = order_totals
        return all_items

    def _make_soup(self) -> None:
        if self.bill_type == "html":
            self.soup = BeautifulSoup(self.bill_data, "html.parser")
        else:
            msg = "Unsupported bill type"
            raise ValueError(msg)

    def _extract_adjusted_items(self) -> dict[str, float]:
        adjusted_table = \
            self.soup.find("table",
                           {"class": InstacartHTMLConstants.adjusted_items_table_class})
        items = {}

        if adjusted_table is None:
            return items

        for item in adjusted_table.select(InstacartHTMLConstants.items_block_class):
            if "weight adjustment" in item.text:
                info = \
                    item.select_one(InstacartHTMLConstants.items_name_class).text.strip().splitlines()
                wanted = info[0]
                delivered = info[0]
                for data in info:
                    if "Adjustment" in data:
                        parsed_data = data.split(" ")
                        original_quantity = parsed_data[1] + " kg"
                        adjusted_quantity = parsed_data[4] + " kg"
                wanted += f" ({original_quantity})"
                delivered += f" ({adjusted_quantity})"
                quantity = adjusted_quantity
                item_name = f"REPLACED:{wanted}->{delivered}"
                delivered_prices = item.select(InstacartHTMLConstants.items_delivered_price_class)
                for price in delivered_prices:
                    if "strike" in price["class"]:
                        continue
                    delivered_price = float(price.text.strip()[1:])
            elif "Refunded amount" in item.text:
                continue
            else:
                wanted = \
                    item.select_one(InstacartHTMLConstants.items_wanted_class).text.strip().splitlines()[0]
                delivered = \
                    item.select_one(InstacartHTMLConstants.items_delivered_class).text.strip().splitlines()[0]
                quantity = \
                    item.select_one(InstacartHTMLConstants.item_quantity_class).text.split("x")[0].strip()
                item_name = f"REPLACED:{wanted}->{delivered}"
                delivered_price = \
                    float(item.select_one(InstacartHTMLConstants.items_delivered_price_class).text.strip()[1:])
            items[item_name] = {
                "price": delivered_price,
                "quantity": quantity,
            }
        return items

    def _extract_found_items(self) -> list[dict[str, str | float]]:
        found_table = \
            self.soup.find("table",
                           {"class": InstacartHTMLConstants.found_items_table_class})
        items = {}
        for item in found_table.select(InstacartHTMLConstants.items_block_class):
            delivered = \
                item.select_one(InstacartHTMLConstants.items_name_class).text.strip().splitlines()[0]
            prices = item.select(InstacartHTMLConstants.items_price_class)
            for price_soup in prices:
                if "strike" in price_soup["class"]:
                    continue
                price = float(price_soup.text.strip()[1:])
            quantity = \
                item.select_one(InstacartHTMLConstants.item_quantity_class).text.split("x")[0].strip()

            items[delivered] = {
                "price": price,
                "quantity": quantity
            }
        return items

    def _extract_order_totals(self)  -> dict[str, float]:
        order_totals = {}
        charges_table = \
            self.soup.find("table", {"class": InstacartHTMLConstants.charges_table_class})
        for item in charges_table.find_all("tr"):
            charge_type = item.select_one(InstacartHTMLConstants.charge_type_class).text.strip()

            if charge_type in InstacartHTMLConstants.ignore_keys:
                continue

            raw_amount = item.select_one(InstacartHTMLConstants.charge_amount_class).text.strip()
            raw_amount = raw_amount.replace("$", "")
            charge_amount = float(raw_amount)
            order_totals[charge_type] = charge_amount

        order_totals["Final Total"] = order_totals[InstacartHTMLConstants.charge_final_name]
        return order_totals
