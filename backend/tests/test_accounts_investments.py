from decimal import Decimal

from fastapi.testclient import TestClient


def _category_id(client: TestClient, name: str) -> int:
    return next(category["id"] for category in client.get("/api/v1/categories").json() if category["name"] == name)


def test_financial_account_crud_snapshot_and_gmail_detection(client: TestClient) -> None:
    account_response = client.post(
        "/api/v1/financial-accounts",
        json={
            "name": "Santander credito 1234",
            "institution": "Santander",
            "account_type": "credit_card",
            "last_four": "1234",
            "opening_balance": "100000.00",
        },
    )
    assert account_response.status_code == 201
    account = account_response.json()

    snapshot_response = client.post(
        f"/api/v1/financial-accounts/{account['id']}/snapshots",
        json={"captured_at": "2026-06-01T00:00:00-04:00", "balance": "100000.00"},
    )
    assert snapshot_response.status_code == 201

    preview = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Santander <avisos@santander.cl>\n"
                "Subject: Compra aprobada tarjeta de credito terminada en 1234 por $15.000\n\n"
                "Tarjeta de credito terminada en 1234.\n"
                "Monto: $15.000\n"
            )
        },
    )
    assert preview.status_code == 201
    candidate = preview.json()
    assert candidate["suggested_financial_account_id"] == account["id"]
    assert candidate["detected_account_type"] == "credit_card"

    response = client.post(
        "/api/v1/import/confirm",
        json={
            "email_message_id": candidate["email_message_id"],
            "import_run_id": candidate["import_run_id"],
            "occurred_at": candidate["received_at"],
            "amount": candidate["amount"],
            "currency": "CLP",
            "merchant_name": "Compra test",
            "category_id": _category_id(client, "Por revisar"),
            "transaction_type": "expense",
            "status": "classified",
            "financial_account_id": account["id"],
            "account_detection_method": "email_parser",
            "account_detection_confidence": candidate["account_detection_confidence"],
            "account_detection_reason": candidate["account_detection_reason"],
        },
    )
    assert response.status_code == 201
    transaction = response.json()["transaction"]
    assert transaction["financial_account"]["id"] == account["id"]

    balance = client.get(f"/api/v1/financial-accounts/{account['id']}/balance")
    assert balance.status_code == 200
    assert Decimal(balance.json()["balance"]) == Decimal("85000.00")


def test_account_detection_handles_current_bancoedwards_and_bancochile_patterns(client: TestClient) -> None:
    edwards = client.post(
        "/api/v1/financial-accounts",
        json={
            "name": "Edwards credito 9876",
            "institution": "Banco Edwards",
            "account_type": "credit_card",
            "last_four": "9876",
        },
    ).json()
    chile = client.post(
        "/api/v1/financial-accounts",
        json={
            "name": "Banco de Chile corriente 4321",
            "institution": "Banco de Chile",
            "account_type": "checking",
            "last_four": "4321",
        },
    ).json()

    purchase = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Banco Edwards <enviodigital@bancoedwards.cl>\n"
                "Subject: Compra con Tarjeta de Crédito\n\n"
                "ALERTA: Este correo proviene de un remitente externo. Ten mucho cuidado con el contenido, enlaces y archivos adjuntos, no los abras a menos que estés seguro.\n"
                "Te informamos que se realizo una compra con Tarjeta de Credito Nro. **** **** **** 9876 por $3.250.\n"
                "Comercio: Farmacia Test\n"
                "Cargo informado en tu tarjeta.\n"
            )
        },
    ).json()

    assert purchase["detected_account_institution"] == "Banco Edwards"
    assert purchase["detected_account_type"] == "credit_card"
    assert purchase["detected_account_last_four"] == "9876"
    assert purchase["suggested_financial_account_id"] == edwards["id"]
    assert purchase["suggested_transaction_type"] == "expense"

    transfer = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Servicio de Transferencias <serviciodetransferencias@bancochile.cl>\n"
                "Subject: Transferencia a Terceros\n\n"
                "Comprobante de Transferencia a terceros.\n"
                "Cuenta Corriente Nro. XXXX-XXXX-4321\n"
                "Monto: $6.000\n"
            )
        },
    ).json()

    assert transfer["detected_account_institution"] == "Banco de Chile"
    assert transfer["detected_account_type"] == "checking"
    assert transfer["detected_account_last_four"] == "4321"
    assert transfer["suggested_financial_account_id"] == chile["id"]
    assert transfer["suggested_transaction_type"] == "transfer_out"


def test_investment_and_disinvestment_do_not_pollute_income_expense(client: TestClient) -> None:
    checking = client.post(
        "/api/v1/financial-accounts",
        json={"name": "Cuenta corriente", "institution": "Banco", "account_type": "checking"},
    ).json()
    client.post(
        "/api/v1/financial-accounts",
        json={"name": "Credito excluido", "institution": "Banco", "account_type": "credit_card", "opening_balance": "100000.00"},
    )
    investment_account = client.post(
        "/api/v1/investment-accounts",
        json={"name": "Fintual objetivo", "institution": "Fintual", "account_type": "mutual_fund"},
    ).json()
    inversiones_id = _category_id(client, "Inversiones")
    desinversiones_id = _category_id(client, "Desinversiones")

    invest = client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-06-03T10:00:00-04:00",
            "amount": "50000.00",
            "category_id": inversiones_id,
            "financial_account_id": checking["id"],
            "investment_account_id": investment_account["id"],
            "transaction_type": "investment",
            "status": "classified",
        },
    )
    assert invest.status_code == 201
    assert Decimal(invest.json()["signed_amount"]) == Decimal("-50000")

    withdraw = client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-06-04T10:00:00-04:00",
            "amount": "12000.00",
            "category_id": desinversiones_id,
            "financial_account_id": checking["id"],
            "investment_account_id": investment_account["id"],
            "transaction_type": "disinvestment",
            "status": "classified",
        },
    )
    assert withdraw.status_code == 201
    assert Decimal(withdraw.json()["signed_amount"]) == Decimal("12000")

    dashboard = client.get("/api/v1/dashboard/overview", params={"year": 2026, "month": 6}).json()
    assert Decimal(dashboard["metrics"]["month_expense"]) == Decimal("0.00")
    assert Decimal(dashboard["metrics"]["month_income"]) == Decimal("0.00")
    assert Decimal(dashboard["metrics"]["liquid_balance"]) == Decimal("-38000.00")
    assert Decimal(dashboard["metrics"]["investment_balance"]) == Decimal("38000.00")
    checking_summary = next(account for account in dashboard["financial_accounts"] if account["name"] == "Cuenta corriente")
    assert Decimal(checking_summary["month_delta"]) == Decimal("-38000.00")
    assert Decimal(dashboard["investment_accounts"][0]["month_invested"]) == Decimal("50000.00")
    assert Decimal(dashboard["investment_accounts"][0]["month_withdrawn"]) == Decimal("12000.00")


def test_editing_investment_transaction_syncs_account_value(client: TestClient) -> None:
    investment_account = client.post(
        "/api/v1/investment-accounts",
        json={"name": "Fintual editable", "institution": "Fintual", "account_type": "mutual_fund"},
    ).json()
    inversiones_id = _category_id(client, "Inversiones")
    desinversiones_id = _category_id(client, "Desinversiones")

    created = client.post(
        "/api/v1/transactions",
        json={
            "occurred_at": "2026-06-03T10:00:00-04:00",
            "amount": "50000.00",
            "category_id": inversiones_id,
            "investment_account_id": investment_account["id"],
            "transaction_type": "investment",
            "status": "classified",
        },
    )
    assert created.status_code == 201
    assert Decimal(client.get("/api/v1/investment-accounts").json()[0]["current_value"]) == Decimal("50000.00")

    updated = client.patch(
        f"/api/v1/transactions/{created.json()['id']}",
        json={
            "amount": "12000.00",
            "category_id": desinversiones_id,
            "transaction_type": "disinvestment",
            "investment_account_id": investment_account["id"],
        },
    )
    assert updated.status_code == 200
    assert Decimal(updated.json()["signed_amount"]) == Decimal("12000")

    accounts = client.get("/api/v1/investment-accounts").json()
    assert Decimal(accounts[0]["current_value"]) == Decimal("-12000.00")
    movements = client.get(f"/api/v1/investment-accounts/{investment_account['id']}/movements").json()
    assert len(movements) == 1
    assert movements[0]["movement_type"] == "disinvestment"
    assert Decimal(movements[0]["amount"]) == Decimal("12000.00")
