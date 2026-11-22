from typing import Any


class ScopeChecker:

    @staticmethod
    def check_tool_permission(
        scope: dict,
        tool_name: str
    ) -> dict:

        if not scope or not scope.get("enabled", False):
            return {
                "allowed": False,
                "reason": "Agent scope is missing or disabled"
            }

        allowed_tools = scope.get("allowed_tools", [])

        if tool_name not in allowed_tools:
            return {
                "allowed": False,
                "reason": f"Tool '{tool_name}' is outside agent scope"
            }

        return {
            "allowed": True,
            "reason": "Tool permitted"
        }

    @staticmethod
    def check_action_permission(
        scope: dict,
        action: str
    ) -> dict:

        if not scope or not scope.get("enabled", False):
            return {
                "allowed": False,
                "reason": "Agent scope is missing or disabled"
            }

        restricted = scope.get("restricted_actions", [])

        if action in restricted:
            return {
                "allowed": False,
                "reason": f"Action '{action}' is explicitly restricted"
            }

        allowed_actions = scope.get("allowed_actions", [])

        if action not in allowed_actions:
            return {
                "allowed": False,
                "reason": f"Action '{action}' is not permitted"
            }

        return {
            "allowed": True,
            "reason": "Action permitted"
        }

    @staticmethod
    def check_resource_permission(
        scope: dict,
        resource: str
    ) -> dict:

        if not scope or not scope.get("enabled", False):
            return {
                "allowed": False,
                "reason": "Agent scope is missing or disabled"
            }

        allowed_resources = scope.get(
            "allowed_resources", []
        )

        if resource not in allowed_resources:
            return {
                "allowed": False,
                "reason": f"Resource '{resource}' is outside agent scope"
            }

        return {
            "allowed": True,
            "reason": "Resource permitted"
        }

    @staticmethod
    def check_topic_permission(
        scope: dict,
        topic: str
    ) -> dict:

        if not scope or not scope.get("enabled", False):
            return {
                "allowed": False,
                "reason": "Agent scope is missing or disabled"
            }

        allowed_topics = scope.get("allowed_topics", [])

        if topic not in allowed_topics:
            return {
                "allowed": False,
                "reason": f"Topic '{topic}' is outside agent scope"
            }

        return {
            "allowed": True,
            "reason": "Topic permitted"
        }

    @staticmethod
    def check_transaction_limit(
        scope: dict,
        amount: float | None
    ) -> dict:

        if not scope or not scope.get("enabled", False):
            return {
                "allowed": False,
                "reason": "Agent scope is missing or disabled"
            }

        limits = scope.get("resource_limits", {})
        max_amount = limits.get("max_transaction_amount")

        if max_amount is None:
            return {
                "allowed": False,
                "reason": "No transaction limit has been configured"
            }

        if amount is None:
            return {
                "allowed": False,
                "reason": "Transaction amount is required for this action"
            }

        if amount < 0 or amount > max_amount:
            return {
                "allowed": False,
                "reason": "Transaction exceeds permitted limit"
            }

        return {
            "allowed": True,
            "reason": "Transaction limit satisfied"
        }

    
    @staticmethod
    def requires_transaction_amount(action: str) -> bool:
        """
        Identify actions that must provide a transaction amount.

        Extend this set when new financial actions are introduced.
        """
        financial_actions = {
            "transfer_funds",
            "transfer",
            "send_payment",
            "make_payment",
            "payment",
            "pay",
            "withdraw",
            "deposit",
            "purchase",
            "charge",
            "refund",
        }

        return action.strip().lower() in financial_actions