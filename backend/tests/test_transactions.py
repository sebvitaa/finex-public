from decimal import Decimal

from fastapi.testclient import TestClient


def _first_category_id(client: TestClient) -> int:
    return client.get("/api/v1/categories").json()[0]["id"]


def _category_id(client: TestClient, name: str) -> int:
    categories = client.get("/api/v1/categories").json()
    return next(category["id"] for category in categories if category["name"] == name)


def test_transaction_crud(client: TestClient) -> None:
    category_id = _first_category_id(client)

    create_response = client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-05-27T12:00:00-04:00",
            "amount": "12990.00",
            "currency": "clp",
            "merchant_name": "Rappi",
            "description": "Almuerzo",
            "category_id": category_id,
            "status": "classified",
            "classification_method": "manual",
        },
    )

    assert create_response.status_code == 201
    transaction = create_response.json()
    assert Decimal(transaction["amount"]) == Decimal("12990.00")
    assert transaction["currency"] == "CLP"
    assert transaction["category"]["id"] == category_id
    assert transaction["relationship_category"] == "mi"

    list_response = client.get("/api/v1/transactions", params={"q": "rappi"})
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    update_response = client.patch(
        f"/api/v1/transactions/{transaction['id']}",
        json={"merchant_name": "Rappi Chile", "amount": "14990.00"},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["merchant_name"] == "Rappi Chile"
    assert Decimal(updated["amount"]) == Decimal("14990.00")

    delete_response = client.delete(f"/api/v1/transactions/{transaction['id']}")
    assert delete_response.status_code == 204

    get_deleted_response = client.get(f"/api/v1/transactions/{transaction['id']}")
    assert get_deleted_response.status_code == 404


def test_transaction_requires_existing_category(client: TestClient) -> None:
    response = client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-05-27T12:00:00-04:00",
            "amount": "5000.00",
            "currency": "CLP",
            "merchant_name": "Metro",
            "category_id": 9999,
        },
    )

    assert response.status_code == 404


def test_transaction_with_lider_splits_and_type_filters(client: TestClient) -> None:
    supermercado_id = _category_id(client, "Supermercado")
    golosinas_id = _category_id(client, "Golosinas")
    comida_id = _category_id(client, "Comida")
    aseo_id = _category_id(client, "Aseo y limpieza")

    create_response = client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-05-29T15:00:00-04:00",
            "amount": "42000.00",
            "currency": "CLP",
            "merchant_name": "Lider",
            "description": "Compra mixta supermercado",
            "category_id": supermercado_id,
            "status": "classified",
            "transaction_type": "expense",
            "splits": [
                {"category_id": golosinas_id, "amount": "8000.00", "label": "Golosinas"},
                {"category_id": comida_id, "amount": "21000.00", "label": "Comida"},
                {"category_id": aseo_id, "amount": "10000.00", "label": "Aseo"},
                {"category_id": supermercado_id, "amount": "3000.00", "label": "Otros"},
            ],
        },
    )

    assert create_response.status_code == 201
    transaction = create_response.json()
    assert Decimal(transaction["signed_amount"]) == Decimal("-42000")
    assert len(transaction["splits"]) == 4

    list_response = client.get("/api/v1/transactions", params={"transaction_type": "expense", "q": "lider"})
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    replace_response = client.put(
        f"/api/v1/transactions/{transaction['id']}/splits",
        json=[
            {"category_id": comida_id, "amount": "22000.00", "label": "Comida ajustada"},
            {"category_id": aseo_id, "amount": "20000.00", "label": "Aseo ajustado"},
        ],
    )
    assert replace_response.status_code == 200
    assert len(replace_response.json()["splits"]) == 2


def test_transaction_relationship_category_is_saved_and_filterable(client: TestClient) -> None:
    category_id = _category_id(client, "Comida")

    create_response = client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-06-02T14:00:00-04:00",
            "amount": "18000.00",
            "currency": "CLP",
            "merchant_name": "Cafe",
            "description": "Salida con amigos",
            "category_id": category_id,
            "relationship_category": "amigos",
            "status": "classified",
            "transaction_type": "expense",
        },
    )

    assert create_response.status_code == 201
    transaction = create_response.json()
    assert transaction["relationship_category"] == "amigos"

    filtered = client.get("/api/v1/transactions", params={"relationship_category": "amigos"})
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [transaction["id"]]


def test_transaction_splits_must_match_amount(client: TestClient) -> None:
    category_id = _first_category_id(client)

    response = client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-05-29T15:00:00-04:00",
            "amount": "10000.00",
            "merchant_name": "Lider",
            "category_id": category_id,
            "splits": [{"category_id": category_id, "amount": "9000.00", "label": "Parte"}],
        },
    )

    assert response.status_code == 400


def test_transaction_clp_rejects_decimals_and_usd_keeps_equivalent(client: TestClient) -> None:
    category_id = _first_category_id(client)

    clp_response = client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-06-06T12:00:00-04:00",
            "amount": "12.50",
            "currency": "CLP",
            "category_id": category_id,
            "transaction_type": "expense",
        },
    )
    assert clp_response.status_code == 422

    usd_response = client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-06-06T12:00:00-04:00",
            "amount": "22.50",
            "currency": "USD",
            "amount_clp": "21150",
            "category_id": category_id,
            "transaction_type": "expense",
            "status": "classified",
        },
    )
    assert usd_response.status_code == 201
    transaction = usd_response.json()
    assert Decimal(transaction["amount"]) == Decimal("22.50")
    assert transaction["currency"] == "USD"
    assert Decimal(transaction["amount_clp"]) == Decimal("21150")
    assert transaction["exchange_rate"] is not None


def test_transaction_rejects_financial_account_currency_mismatch(client: TestClient) -> None:
    category_id = _first_category_id(client)
    clp_card = next(account for account in client.get("/api/v1/financial-accounts").json() if account["name"] == "Credito CLP · 7459")

    response = client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-06-06T12:00:00-04:00",
            "amount": "22.00",
            "currency": "USD",
            "category_id": category_id,
            "financial_account_id": clp_card["id"],
            "transaction_type": "expense",
        },
    )

    assert response.status_code == 400
    assert "currency" in response.json()["detail"].lower()


def test_income_internal_payable_reduces_own_income(client: TestClient) -> None:
    person = client.post("/api/v1/people", json={"name": "Socio clase"}).json()
    category_id = _category_id(client, "Clases")

    response = client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-06-05T12:00:00-04:00",
            "amount": "72000.00",
            "currency": "CLP",
            "counterparty": "Alumno",
            "category_id": category_id,
            "transaction_type": "income",
            "status": "classified",
            "internal_payables": [{"person_id": person["id"], "title": "Parte clase compartida", "amount": "12000.00"}],
        },
    )

    assert response.status_code == 201
    transaction = response.json()
    assert Decimal(transaction["amount"]) == Decimal("60000.00")
    assert Decimal(transaction["signed_amount"]) == Decimal("60000")

    payables = client.get("/api/v1/payables").json()
    payable = next(item for item in payables if item["person_id"] == person["id"])
    assert payable["title"] == "Parte clase compartida"
    assert Decimal(payable["remaining_amount"]) == Decimal("12000.00")


def _create_checking_account(client: TestClient, name: str, opening: str, currency: str = "CLP") -> dict:
    response = client.post(
        "/api/v1/financial-accounts",
        json={
            "name": name,
            "institution": "Banco",
            "account_type": "checking",
            "currency": currency,
            "opening_balance": opening,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_internal_transfer_moves_capital_without_income_or_expense(client: TestClient) -> None:
    origin = _create_checking_account(client, "Cuenta corriente", "200000.00")
    destination = _create_checking_account(client, "Cuenta ahorro", "50000.00")

    response = client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-06-10T12:00:00-04:00",
            "amount": "80000.00",
            "currency": "CLP",
            "description": "Paso a ahorro",
            "transaction_type": "internal_transfer",
            "status": "classified",
            "financial_account_id": origin["id"],
            "destination_account_id": destination["id"],
        },
    )

    assert response.status_code == 201
    transaction = response.json()
    assert transaction["transaction_type"] == "internal_transfer"
    assert transaction["destination_account"]["id"] == destination["id"]
    assert Decimal(transaction["destination_amount"]) == Decimal("80000.00")
    assert transaction["destination_currency"] == "CLP"
    # Origin leg is negative; the transfer is net-zero capital movement.
    assert Decimal(transaction["signed_amount"]) == Decimal("-80000")

    dashboard = client.get("/api/v1/dashboard/overview", params={"year": 2026, "month": 6}).json()
    assert Decimal(dashboard["metrics"]["month_expense"]) == Decimal("0")
    assert Decimal(dashboard["metrics"]["month_income"]) == Decimal("0")

    balances = {account["account_id"]: account for account in dashboard["financial_accounts"]}
    assert Decimal(balances[origin["id"]]["balance"]) == Decimal("120000.00")
    assert Decimal(balances[destination["id"]]["balance"]) == Decimal("130000.00")


def test_internal_transfer_requires_distinct_destination(client: TestClient) -> None:
    origin = _create_checking_account(client, "Cuenta corriente", "200000.00")

    missing = client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-06-10T12:00:00-04:00",
            "amount": "80000.00",
            "currency": "CLP",
            "transaction_type": "internal_transfer",
            "financial_account_id": origin["id"],
        },
    )
    assert missing.status_code == 400

    same = client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-06-10T12:00:00-04:00",
            "amount": "80000.00",
            "currency": "CLP",
            "transaction_type": "internal_transfer",
            "financial_account_id": origin["id"],
            "destination_account_id": origin["id"],
        },
    )
    assert same.status_code == 400
