
import pytest

from app.services.security.scope_checker import ScopeChecker


@pytest.mark.parametrize(
    "checker, argument",
    [
        (ScopeChecker.check_action_permission, "read_invoice"),
        (ScopeChecker.check_resource_permission, "invoice_records"),
        (ScopeChecker.check_topic_permission, "research"),
        (ScopeChecker.check_transaction_limit, 100.0),
    ],
)
@pytest.mark.parametrize(
    "scope",
    [
        None,
        {"enabled": False},
    ],
)
def test_permission_checks_reject_missing_or_disabled_scope(
    checker,
    argument,
    scope,
):
    result = checker(scope, argument)

    assert result["allowed"] is False
    assert result["reason"] == "Agent scope is missing or disabled"


def test_action_not_in_allowlist_is_denied():
    scope = {
        "enabled": True,
        "allowed_actions": ["read_invoice"],
        "restricted_actions": [],
    }

    result = ScopeChecker.check_action_permission(
        scope,
        "delete_invoice",
    )

    assert result["allowed"] is False
    assert result["reason"] == (
        "Action 'delete_invoice' is not permitted"
    )
