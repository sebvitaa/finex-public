from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _category_id(client: TestClient, name: str) -> int:
    return next(category["id"] for category in client.get("/api/v1/categories").json() if category["name"] == name)


def test_seeded_rules_classify_spotify_and_uber(client: TestClient) -> None:
    spotify = client.post("/api/v1/rules/test", json={"raw_text": "Cargo aprobado Spotify $4.550"}).json()
    assert spotify["category_name"] == "Suscripciones"
    assert spotify["transaction_type"] == "subscription"
    assert spotify["confidence"] >= 0.8
    assert spotify["matched_rules"][0]["rule_name"] == "Spotify a suscripciones"

    uber = client.post("/api/v1/rules/test", json={"raw_text": "Compra por $12.990 en UBER TRIP"}).json()
    assert uber["category_name"] == "Transporte"
    assert uber["transaction_type"] == "expense"


def test_rule_overrides_import_candidate_with_explainable_reason(client: TestClient) -> None:
    preview = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Spotify <no-reply@spotify.com>\n"
                "Subject: Cargo aprobado Spotify $4.550\n\n"
                "Total: $4.550\n"
            )
        },
    ).json()

    assert preview["suggested_category_name"] == "Suscripciones"
    assert preview["suggested_transaction_type"] == "subscription"
    assert preview["classification_method"] == "rule_engine"
    assert "Spotify a suscripciones" in preview["classification_reason"]


def test_custom_rule_can_target_financial_account(client: TestClient) -> None:
    account = client.post(
        "/api/v1/financial-accounts",
        json={"name": "Edwards 9876", "institution": "Banco Edwards", "account_type": "credit_card", "last_four": "9876"},
    ).json()
    rule = client.post(
        "/api/v1/rules",
        json={
            "name": "Banco Edwards tarjeta 9876",
            "field": "source_text",
            "operator": "contains",
            "pattern": "9876",
            "financial_account_id": account["id"],
            "priority": 1,
            "confidence": 0.93,
        },
    )
    assert rule.status_code == 201

    result = client.post(
        "/api/v1/rules/test",
        json={"raw_text": "Compra con Tarjeta de Credito terminada en 9876 por $3.250"},
    ).json()
    assert result["financial_account_id"] == account["id"]
    assert result["financial_account_name"] == "Edwards 9876"


def test_transaction_corrections_generate_rule_suggestions(client: TestClient, db_session: Session) -> None:
    comida_id = _category_id(client, "Comida")
    transporte_id = _category_id(client, "Transporte")
    created = []
    for index in range(2):
        response = client.post(
            "/api/v1/transactions",
            json={
                "occurred_at": f"2026-06-0{index + 1}T12:00:00-04:00",
                "amount": "12990.00",
                "merchant_name": "Uber Trip",
                "category_id": comida_id,
                "transaction_type": "expense",
                "status": "classified",
            },
        )
        assert response.status_code == 201
        created.append(response.json())

    for transaction in created:
        update = client.patch(f"/api/v1/transactions/{transaction['id']}", json={"category_id": transporte_id})
        assert update.status_code == 200

    suggestions = client.get("/api/v1/rules/suggestions").json()
    suggestion = next(item for item in suggestions if item["pattern"] == "Uber Trip")
    assert suggestion["category_name"] == "Transporte"
    assert suggestion["count"] == 2

    feedback = client.get("/api/v1/rules/feedback").json()
    assert len(feedback) == 2
    assert Decimal(str(feedback[0]["confidence"])) > Decimal("0.5")
