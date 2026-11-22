from app.services.security.scope_checker import ScopeChecker


SCOPE = {
    "enabled": True,

    "allowed_tools": [
        "get_invoice",
        "get_supplier"
    ],

    "allowed_actions": [
        "read_invoice"
    ],

    "restricted_actions": [
        "modify_payroll"
    ],

    "allowed_resources": [
        "invoice_records"
    ],

    "allowed_topics": [
        "finance"
    ],

    "resource_limits": {
        "max_transaction_amount": 10000
    }
}


def test_allowed_tool():

    result = ScopeChecker.check_tool_permission(
        SCOPE,
        "get_invoice"
    )

    assert result["allowed"] is True


def test_unauthorized_tool():

    result = ScopeChecker.check_tool_permission(
        SCOPE,
        "delete_employee"
    )

    assert result["allowed"] is False


def test_restricted_action():

    result = ScopeChecker.check_action_permission(
        SCOPE,
        "modify_payroll"
    )

    assert result["allowed"] is False


def test_transaction_limit():

    result = ScopeChecker.check_transaction_limit(
        SCOPE,
        15000
    )

    assert result["allowed"] is False


def test_missing_scope():

    result = ScopeChecker.check_tool_permission(
        {},
        "get_invoice"
    )

    assert result["allowed"] is False


def test_disabled_scope():

    disabled_scope = {
        **SCOPE,
        "enabled": False
    }

    result = ScopeChecker.check_tool_permission(
        disabled_scope,
        "get_invoice"
    )

    assert result["allowed"] is False