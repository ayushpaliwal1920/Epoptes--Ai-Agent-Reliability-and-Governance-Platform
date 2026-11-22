
import pytest

from app.services.security.scope_checker import ScopeChecker


@pytest.fixture
def allowed_scope():
    return {
        "enabled": True,
        "allowed_tools": ["get_invoice", "search_records"],
        "allowed_actions": ["read_invoice", "search"],
        "restricted_actions": ["delete", "transfer_funds"],
        "allowed_resources": ["invoice_records", "public_records"],
        "allowed_topics": ["research", "general"],
        "resource_limits": {
            "max_transaction_amount": 1000.0
        },
    }


# -------------------------------------------------
# Tool permissions
# -------------------------------------------------

def test_allowed_tool(allowed_scope):
    result = ScopeChecker.check_tool_permission(
        allowed_scope,
        "get_invoice"
    )

    assert result["allowed"] is True


def test_disallowed_tool(allowed_scope):
    result = ScopeChecker.check_tool_permission(
        allowed_scope,
        "delete_invoice"
    )

    assert result["allowed"] is False


# -------------------------------------------------
# Action permissions
# -------------------------------------------------

def test_allowed_action(allowed_scope):
    result = ScopeChecker.check_action_permission(
        allowed_scope,
        "read_invoice"
    )

    assert result["allowed"] is True


def test_restricted_action_is_denied(allowed_scope):
    result = ScopeChecker.check_action_permission(
        allowed_scope,
        "transfer_funds"
    )

    assert result["allowed"] is False
    assert "explicitly restricted" in result["reason"]


def test_restricted_action_overrides_allowed_action(allowed_scope):
    allowed_scope["allowed_actions"].append("transfer_funds")

    result = ScopeChecker.check_action_permission(
        allowed_scope,
        "transfer_funds"
    )

    assert result["allowed"] is False
    assert "explicitly restricted" in result["reason"]


# -------------------------------------------------
# Resource permissions
# -------------------------------------------------

def test_allowed_resource(allowed_scope):
    result = ScopeChecker.check_resource_permission(
        allowed_scope,
        "invoice_records"
    )

    assert result["allowed"] is True


def test_disallowed_resource(allowed_scope):
    result = ScopeChecker.check_resource_permission(
        allowed_scope,
        "employee_records"
    )

    assert result["allowed"] is False


# -------------------------------------------------
# Topic permissions
# -------------------------------------------------

def test_allowed_topic(allowed_scope):
    result = ScopeChecker.check_topic_permission(
        allowed_scope,
        "research"
    )

    assert result["allowed"] is True


def test_disallowed_topic(allowed_scope):
    result = ScopeChecker.check_topic_permission(
        allowed_scope,
        "finance"
    )

    assert result["allowed"] is False


# -------------------------------------------------
# Disabled or missing scope
# -------------------------------------------------

@pytest.mark.parametrize(
    "scope",
    [
        None,
        {},
        {"enabled": False},
    ],
)
def test_missing_or_disabled_scope_denies_permissions(scope):
    result = ScopeChecker.check_tool_permission(
        scope,
        "get_invoice"
    )

    assert result["allowed"] is False


# -------------------------------------------------
# Transaction limits
# -------------------------------------------------

def test_transaction_within_limit(allowed_scope):
    result = ScopeChecker.check_transaction_limit(
        allowed_scope,
        500.0
    )

    assert result["allowed"] is True


def test_transaction_at_exact_limit(allowed_scope):
    result = ScopeChecker.check_transaction_limit(
        allowed_scope,
        1000.0
    )

    assert result["allowed"] is True


def test_transaction_above_limit(allowed_scope):
    result = ScopeChecker.check_transaction_limit(
        allowed_scope,
        1500.0
    )

    assert result["allowed"] is False


def test_missing_transaction_amount_is_denied(allowed_scope):
    result = ScopeChecker.check_transaction_limit(
        allowed_scope,
        None
    )

    assert result["allowed"] is False
    assert "amount is required" in result["reason"]


def test_negative_transaction_amount_is_denied(allowed_scope):
    result = ScopeChecker.check_transaction_limit(
        allowed_scope,
        -100.0
    )

    assert result["allowed"] is False


def test_missing_transaction_limit_is_denied(allowed_scope):
    allowed_scope["resource_limits"] = {}

    result = ScopeChecker.check_transaction_limit(
        allowed_scope,
        100.0
    )

    assert result["allowed"] is False


# -------------------------------------------------
# Financial action classification
# -------------------------------------------------

@pytest.mark.parametrize(
    "action",
    [
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
    ],
)
def test_financial_actions_require_amount(action):
    assert ScopeChecker.requires_transaction_amount(action) is True


@pytest.mark.parametrize(
    "action",
    [
        "read_invoice",
        "search",
        "view_profile",
        "general",
    ],
)
def test_non_financial_actions_do_not_require_amount(action):
    assert ScopeChecker.requires_transaction_amount(action) is False


def test_financial_action_matching_ignores_case_and_whitespace():
    assert ScopeChecker.requires_transaction_amount(
        "  TRANSFER_FUNDS  "
    ) is True
