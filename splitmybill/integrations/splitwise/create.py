from __future__ import annotations

from pathlib import Path

import yaml
from splitwise import Splitwise
from splitwise.expense import Expense
from splitwise.user import ExpenseUser


def create_expense(cost: float,
                   description: str,
                   user_shares: dict[str, float],
                   config:  dict | str,
                   **kwargs,  # noqa: ARG001
    ) -> None:
    """Create a Splitwise expense using config credentials.

    Args:
        config (dict): Dictionary containing auth credentials with keys:
                      - consumer_key
                      - consumer_secret
                      - api_key
        cost (str): Total cost of the expense
        description (str): Description of the expense
        user_shares (list): List of dicts with user_id, paid_share and owed_share
                          [{
                              "user_id": 123,
                              "paid_share": "10.00",
                              "owed_share": "5.00"
                          }]
        **kwargs: Additional kwargs to pass to the expense creation

    Returns:
        tuple: (Expense object, errors)

    Raises:
        FileNotFoundError: if config is a str and file does not exist
    """
    if isinstance(config, str):
        config_path = Path(config)
        if not config_path.exists():
            raise FileNotFoundError(config)
        with config_path.open() as f:
            config = yaml.safe_load(f)

    # Initialize Splitwise with config
    sw_obj = Splitwise(
        config["consumer_key"],
        config["consumer_secret"],
        api_key=config["api_key"]
    )

    # Create expense
    expense = Expense()
    expense.setCost(cost)
    expense.setDescription(description)

    # Add users and their shares
    users = [
        ExpenseUser(
            id=share["user_id"],
            paid_share=share["paid_share"],
            owed_share=share["owed_share"]
        ) for share in user_shares
    ]
    expense.setUsers(users)

    return sw_obj.createExpense(expense)
