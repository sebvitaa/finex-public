from decimal import Decimal

from fastapi.testclient import TestClient


def test_people_and_receivable_partial_payment(client: TestClient) -> None:
    person_response = client.post(
        "/api/v1/people",
        json={"name": "Alumno demo", "alias": "Mateo", "notes": "Clases de matematica"},
    )
    assert person_response.status_code == 201
    person = person_response.json()

    receivable_response = client.post(
        "/api/v1/receivables",
        json={
            "person_id": person["id"],
            "title": "Clase particular",
            "original_amount": "30000.00",
            "currency": "CLP",
            "issued_at": "2026-05-29T12:00:00-04:00",
            "notes": "Pago pendiente por clase",
        },
    )
    assert receivable_response.status_code == 201
    receivable = receivable_response.json()
    assert Decimal(receivable["remaining_amount"]) == Decimal("30000.00")
    assert receivable["status"] == "pending_payment"

    payment_response = client.post(
        f"/api/v1/receivables/{receivable['id']}/payments",
        json={
            "paid_at": "2026-05-29T18:00:00-04:00",
            "amount": "12000.00",
            "notes": "Abono",
        },
    )
    assert payment_response.status_code == 201

    updated_response = client.get(f"/api/v1/receivables/{receivable['id']}")
    assert updated_response.status_code == 200
    updated = updated_response.json()
    assert Decimal(updated["remaining_amount"]) == Decimal("18000.00")
    assert updated["status"] == "partially_paid"
    assert len(updated["payments"]) == 1


def test_receivable_batch_payment_can_cover_multiple_pending_debts(client: TestClient) -> None:
    person = client.post("/api/v1/people", json={"name": "Amigo demo"}).json()

    first = client.post(
        "/api/v1/receivables",
        json={
            "person_id": person["id"],
            "title": "Almuerzo",
            "original_amount": "15000.00",
            "currency": "CLP",
            "issued_at": "2026-06-02T12:00:00-04:00",
        },
    ).json()
    second = client.post(
        "/api/v1/receivables",
        json={
            "person_id": person["id"],
            "title": "Entrada concierto",
            "original_amount": "22000.00",
            "currency": "CLP",
            "issued_at": "2026-06-02T12:30:00-04:00",
        },
    ).json()

    payment_response = client.post(
        "/api/v1/receivables/payments",
        json={
            "paid_at": "2026-06-02T18:00:00-04:00",
            "payments": [
                {"receivable_id": first["id"], "amount": "15000.00"},
                {"receivable_id": second["id"], "amount": "7000.00"},
            ],
        },
    )

    assert payment_response.status_code == 201
    assert len(payment_response.json()) == 2

    updated_first = client.get(f"/api/v1/receivables/{first['id']}").json()
    updated_second = client.get(f"/api/v1/receivables/{second['id']}").json()
    assert updated_first["status"] == "paid"
    assert Decimal(updated_first["remaining_amount"]) == Decimal("0.00")
    assert updated_second["status"] == "partially_paid"
    assert Decimal(updated_second["remaining_amount"]) == Decimal("15000.00")


def test_payable_partial_payment_and_offset_against_receivable(client: TestClient) -> None:
    person = client.post("/api/v1/people", json={"name": "Persona balance"}).json()
    receivable = client.post(
        "/api/v1/receivables",
        json={
            "person_id": person["id"],
            "title": "Me debe supermercado",
            "original_amount": "18000.00",
            "currency": "CLP",
            "issued_at": "2026-06-02T12:00:00-04:00",
        },
    ).json()
    payable = client.post(
        "/api/v1/payables",
        json={
            "person_id": person["id"],
            "title": "Le debo entrada",
            "original_amount": "12000.00",
            "currency": "CLP",
            "issued_at": "2026-06-02T12:30:00-04:00",
        },
    ).json()

    payment_response = client.post(
        f"/api/v1/payables/{payable['id']}/payments",
        json={"paid_at": "2026-06-02T14:00:00-04:00", "amount": "2000.00"},
    )
    assert payment_response.status_code == 201
    payable = client.get(f"/api/v1/payables/{payable['id']}").json()
    assert Decimal(payable["remaining_amount"]) == Decimal("10000.00")
    assert payable["status"] == "partially_paid"

    offset_response = client.post(
        "/api/v1/receivables/offsets",
        json={
            "person_id": person["id"],
            "receivable_id": receivable["id"],
            "payable_id": payable["id"],
            "offset_at": "2026-06-02T15:00:00-04:00",
        },
    )
    assert offset_response.status_code == 201
    offset = offset_response.json()
    assert Decimal(offset["amount"]) == Decimal("10000.00")
    assert offset["resulting_direction"] == "receivable"
    assert Decimal(offset["resulting_amount"]) == Decimal("8000.00")

    updated_receivable = client.get(f"/api/v1/receivables/{receivable['id']}").json()
    updated_payable = client.get(f"/api/v1/payables/{payable['id']}").json()
    assert Decimal(updated_receivable["remaining_amount"]) == Decimal("8000.00")
    assert updated_payable["status"] == "paid"


def test_income_transaction_can_be_linked_to_person(client: TestClient) -> None:
    clases_id = next(category["id"] for category in client.get("/api/v1/categories").json() if category["name"] == "Clases")
    person = client.post("/api/v1/people", json={"name": "Sofia alumna"}).json()

    response = client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-05-29T19:00:00-04:00",
            "amount": "25000.00",
            "currency": "CLP",
            "counterparty": "Sofia alumna",
            "description": "Ingreso por clase",
            "category_id": clases_id,
            "person_id": person["id"],
            "transaction_type": "income",
            "status": "classified",
        },
    )

    assert response.status_code == 201
    transaction = response.json()
    assert transaction["person"]["id"] == person["id"]
    assert Decimal(transaction["signed_amount"]) == Decimal("25000")

    filtered = client.get("/api/v1/transactions", params={"person_id": person["id"], "transaction_type": "income"})
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
