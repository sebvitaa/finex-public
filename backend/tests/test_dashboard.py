from decimal import Decimal

from fastapi.testclient import TestClient


def _category_id(client: TestClient, name: str) -> int:
    return next(category["id"] for category in client.get("/api/v1/categories").json() if category["name"] == name)


def test_dashboard_overview_uses_splits_income_and_receivables(client: TestClient) -> None:
    supermercado_id = _category_id(client, "Supermercado")
    golosinas_id = _category_id(client, "Golosinas")
    comida_id = _category_id(client, "Comida")
    aseo_id = _category_id(client, "Aseo y limpieza")
    clases_id = _category_id(client, "Clases")

    person = client.post("/api/v1/people", json={"name": "Alumno dashboard"}).json()
    client.post(
        "/api/v1/receivables",
        json={
            "person_id": person["id"],
            "title": "Clase pendiente",
            "original_amount": "30000.00",
            "issued_at": "2026-05-12T12:00:00-04:00",
            "due_at": "2026-05-30T12:00:00-04:00",
        },
    )
    client.post(
        "/api/v1/payables",
        json={
            "person_id": person["id"],
            "title": "Material pendiente",
            "original_amount": "12000.00",
            "issued_at": "2026-05-13T12:00:00-04:00",
            "due_at": "2026-05-25T12:00:00-04:00",
        },
    )
    client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-04-10T15:00:00-04:00",
            "amount": "10000.00",
            "merchant_name": "Metro",
            "category_id": comida_id,
            "transaction_type": "expense",
            "status": "classified",
        },
    )
    client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-05-10T15:00:00-04:00",
            "amount": "42000.00",
            "merchant_name": "Lider",
            "description": "Compra mixta",
            "category_id": supermercado_id,
            "transaction_type": "expense",
            "status": "classified",
            "splits": [
                {"category_id": golosinas_id, "amount": "8000.00", "label": "Golosinas"},
                {"category_id": comida_id, "amount": "21000.00", "label": "Comida"},
                {"category_id": aseo_id, "amount": "10000.00", "label": "Aseo"},
                {"category_id": supermercado_id, "amount": "3000.00", "label": "Otros"},
            ],
        },
    )
    client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-05-11T16:00:00-04:00",
            "amount": "25000.00",
            "counterparty": "Alumno dashboard",
            "description": "Ingreso por clase",
            "category_id": clases_id,
            "person_id": person["id"],
            "transaction_type": "income",
            "status": "classified",
        },
    )

    response = client.get("/api/v1/dashboard/overview", params={"year": 2026, "month": 5})

    assert response.status_code == 200
    dashboard = response.json()
    assert Decimal(dashboard["metrics"]["month_expense"]) == Decimal("42000.00")
    assert Decimal(dashboard["metrics"]["month_income"]) == Decimal("25000.00")
    assert Decimal(dashboard["metrics"]["net_balance"]) == Decimal("-17000.00")
    assert Decimal(dashboard["metrics"]["pending_receivables"]) == Decimal("30000.00")

    expense_totals = {category["name"]: Decimal(category["amount"]) for category in dashboard["expense_categories"]}
    assert expense_totals["Golosinas"] == Decimal("8000.00")
    assert expense_totals["Comida"] == Decimal("21000.00")
    assert expense_totals["Aseo y limpieza"] == Decimal("10000.00")

    income_totals = {category["name"]: Decimal(category["amount"]) for category in dashboard["income_categories"]}
    assert income_totals["Clases"] == Decimal("25000.00")
    assert dashboard["unallocated_supermarkets"] == []
    assert len(dashboard["daily_heatmap"]) == 31
    assert Decimal(dashboard["period_comparison"]["expense_delta"]) == Decimal("32000.00")
    assert dashboard["insights"][0]["kind"] in {"daily_spike", "new_merchant"}

    budgets = {budget["name"]: budget for budget in dashboard["budget_progress"]}
    assert Decimal(budgets["Golosinas"]["spent_amount"]) == Decimal("8000.00")
    assert dashboard["class_income_by_person"][0]["person_name"] == "Alumno dashboard"
    assert Decimal(dashboard["receivables_by_person"][0]["amount"]) == Decimal("30000.00")
    assert Decimal(dashboard["payables_by_person"][0]["amount"]) == Decimal("12000.00")
    assert Decimal(dashboard["mixed_purchase_totals"][0]["amount"]) > Decimal("0.00")

    csv_response = client.get("/api/v1/dashboard/export.csv", params={"year": 2026, "month": 5})
    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.headers["content-type"]
    assert "Lider" in csv_response.text
    assert "Golosinas" in csv_response.text


def test_dashboard_flags_unallocated_supermarkets_and_subscriptions(client: TestClient) -> None:
    supermercado_id = _category_id(client, "Supermercado")
    suscripciones_id = _category_id(client, "Suscripciones")

    client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-05-12T15:00:00-04:00",
            "amount": "18000.00",
            "merchant_name": "Jumbo",
            "category_id": supermercado_id,
            "transaction_type": "expense",
            "status": "classified",
        },
    )
    for occurred_at in ["2026-04-01T09:00:00-04:00", "2026-05-01T09:00:00-04:00"]:
        client.post(
            "/api/v1/transactions",
            json={
                "occurred_at": occurred_at,
                "amount": "4550.00",
                "merchant_name": "Spotify",
                "category_id": suscripciones_id,
                "transaction_type": "subscription",
                "status": "classified",
            },
        )

    response = client.get("/api/v1/dashboard/overview", params={"year": 2026, "month": 5})

    assert response.status_code == 200
    dashboard = response.json()
    assert dashboard["unallocated_supermarkets"][0]["merchant_name"] == "Jumbo"
    assert dashboard["subscriptions"][0]["merchant_name"] == "Spotify"
    assert Decimal(dashboard["subscriptions"][0]["average_amount"]) == Decimal("4550.00")


def test_dashboard_uses_amount_clp_and_separates_credit_card_currencies(client: TestClient) -> None:
    category_id = _category_id(client, "Compras online")
    accounts = client.get("/api/v1/financial-accounts").json()
    clp_card = next(account for account in accounts if account["name"] == "Credito CLP · 7459")
    usd_card = next(account for account in accounts if account["name"] == "Credito USD · 7459")

    client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-06-03T12:00:00-04:00",
            "amount": "1000.00",
            "currency": "CLP",
            "category_id": category_id,
            "financial_account_id": clp_card["id"],
            "transaction_type": "expense",
            "status": "classified",
        },
    )
    client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-06-04T12:00:00-04:00",
            "amount": "22.00",
            "currency": "USD",
            "category_id": category_id,
            "financial_account_id": usd_card["id"],
            "transaction_type": "expense",
            "status": "classified",
        },
    )
    client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-06-05T12:00:00-04:00",
            "amount": "10.00",
            "currency": "USD",
            "amount_clp": "9500",
            "category_id": category_id,
            "financial_account_id": usd_card["id"],
            "transaction_type": "expense",
            "status": "classified",
        },
    )

    dashboard = client.get("/api/v1/dashboard/overview", params={"year": 2026, "month": 6}).json()
    assert Decimal(dashboard["metrics"]["month_expense"]) == Decimal("10500.00")

    clp_summary = next(account for account in dashboard["financial_accounts"] if account["account_id"] == clp_card["id"])
    usd_summary = next(account for account in dashboard["financial_accounts"] if account["account_id"] == usd_card["id"])
    assert clp_summary["currency"] == "CLP"
    assert Decimal(clp_summary["used_credit_amount"]) == Decimal("1000.00")
    assert Decimal(clp_summary["available_credit_amount"]) == Decimal("999000.00")
    assert usd_summary["currency"] == "USD"
    assert Decimal(usd_summary["used_credit_amount"]) == Decimal("32.00")
    assert Decimal(usd_summary["available_credit_amount"]) == Decimal("968.00")
