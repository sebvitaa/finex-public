from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import EmailMessage, ImportRun, Payable, Receivable, Transaction


def _category_id(client: TestClient, name: str) -> int:
    categories = client.get("/api/v1/categories").json()
    return next(category["id"] for category in categories if category["name"] == name)


def test_preview_text_import_marks_supermarket_without_detail(client: TestClient, db_session: Session) -> None:
    response = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Banco Demo <avisos@banco.demo>\n"
                "Subject: Compra aprobada Lider por $42.000\n\n"
                "Comercio: Lider\n"
                "Monto: $42.000\n"
                "No se incluye detalle de productos."
            )
        },
    )

    assert response.status_code == 201
    candidate = response.json()
    assert candidate["merchant_name"] == "Lider"
    assert Decimal(candidate["amount"]) == Decimal("42000.00")
    assert candidate["suggested_category_name"] == "Supermercado"
    assert candidate["suggested_transaction_type"] == "expense"
    assert candidate["cashflow_direction"] == "outflow"
    assert candidate["status"] == "needs_review"
    assert candidate["needs_split"] is True
    assert "No se incluye detalle de productos." in candidate["body_text"]

    email_message = db_session.get(EmailMessage, candidate["email_message_id"])
    import_run = db_session.get(ImportRun, candidate["import_run_id"])
    assert email_message is not None
    assert email_message.parse_status == "parsed"
    assert "No se incluye detalle de productos." in (email_message.body_text or "")
    assert import_run is not None
    assert import_run.messages_imported == 1


def test_confirm_import_creates_transaction_and_updates_message(client: TestClient, db_session: Session) -> None:
    preview = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Banco Demo <avisos@banco.demo>\n"
                "Subject: Compra aprobada Rappi $13.990\n\n"
                "Comercio: Rappi\n"
                "Monto: $13.990\n"
                "Descripcion: delivery almuerzo."
            )
        },
    ).json()

    response = client.post(
        "/api/v1/import/confirm",
        json={
            "email_message_id": preview["email_message_id"],
            "import_run_id": preview["import_run_id"],
            "occurred_at": preview["received_at"],
            "amount": preview["amount"],
            "currency": "CLP",
            "merchant_name": preview["merchant_name"],
            "description": preview["description"],
            "subject": preview["subject"],
            "category_id": preview["suggested_category_id"],
            "transaction_type": preview["suggested_transaction_type"],
            "status": "classified",
            "confidence": preview["confidence"],
            "classification_reason": preview["classification_reason"],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["transaction"]["merchant_name"] == "Rappi"
    assert payload["transaction"]["source"] == "gmail"
    assert payload["transaction"]["source_message_id"] == f"email:{preview['email_message_id']}"
    assert Decimal(payload["transaction"]["signed_amount"]) == Decimal("-13990")

    email_message = db_session.get(EmailMessage, preview["email_message_id"])
    assert email_message is not None
    assert email_message.parse_status == "confirmed"


def test_received_transfer_can_be_saved_as_receivable_payment(client: TestClient, db_session: Session) -> None:
    person = client.post("/api/v1/people", json={"name": "Camila Alumna", "alias": "Cami"}).json()
    receivable = client.post(
        "/api/v1/receivables",
        json={
            "person_id": person["id"],
            "title": "Clase pendiente",
            "original_amount": "25000.00",
            "currency": "CLP",
            "issued_at": "2026-05-29T12:00:00-04:00",
        },
    ).json()
    preview = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Banco Demo <avisos@banco.demo>\n"
                "Subject: Transferencia recibida pago clase matematica $25.000\n\n"
                "Recibiste una transferencia.\n"
                "De: Camila Alumna\n"
                "Monto: $25.000\n"
                "Motivo: Pago clase matematica y ayudantia."
            )
        },
    ).json()

    assert preview["suggested_transaction_type"] == "income"
    assert preview["cashflow_direction"] == "inflow"
    assert preview["suggested_category_name"] == "Clases"
    assert preview["counterparty"] == "Camila Alumna"

    response = client.post(
        "/api/v1/import/confirm",
        json={
            "email_message_id": preview["email_message_id"],
            "import_run_id": preview["import_run_id"],
            "occurred_at": preview["received_at"],
            "amount": preview["amount"],
            "currency": "CLP",
            "counterparty": "Camila Alumna",
            "person_id": person["id"],
            "receivable_id": receivable["id"],
            "description": preview["description"],
            "subject": preview["subject"],
            "category_id": _category_id(client, "Cuentas por cobrar"),
            "transaction_type": "receivable_payment",
            "status": "paid",
            "confidence": preview["confidence"],
            "classification_reason": "Usuario marco la transferencia como pago de deuda",
        },
    )

    assert response.status_code == 201
    transaction = response.json()["transaction"]
    assert transaction["transaction_type"] == "receivable_payment"
    assert Decimal(transaction["signed_amount"]) == Decimal("25000")

    updated = db_session.scalar(select(Receivable).where(Receivable.id == receivable["id"]))
    assert updated is not None
    assert updated.remaining_amount == Decimal("0.00")
    assert updated.status == "paid"


def test_import_detects_cashflow_direction_from_bank_words(client: TestClient) -> None:
    incoming = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Banco Bci <avisos@bci.cl>\n"
                "Subject: Transferencia recibida\n\n"
                "Hola\n"
                "Persona Demo\n\n"
                "Has recibido una transferencia de fondos de Persona Remitente Demo hacia tu cuenta del Banco de Chile / Edwards / Credichile\n\n"
                "Datos de la transferencia\n\n"
                "Monto recibido\t$24.000\n"
                "Banco de origen\tBanco Bci / Mach\n"
                "Fecha de la transferencia\t04/06/2026\n"
                "Mensaje\tSin mensaje\n"
                "Numero de comprobante\t1180759731"
            )
        },
    )

    assert incoming.status_code == 201
    incoming_candidate = incoming.json()
    assert Decimal(incoming_candidate["amount"]) == Decimal("24000.00")
    assert incoming_candidate["suggested_transaction_type"] == "transfer_in"
    assert incoming_candidate["cashflow_direction"] == "inflow"
    assert incoming_candidate["suggested_category_name"] == "Transferencias"
    assert incoming_candidate["counterparty"] == "Persona Remitente Demo"

    outgoing = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Banco Edwards <avisos@bancoedwards.cl>\n"
                "Subject: Compra con Tarjeta de Credito\n\n"
                "Persona Demo:\n"
                "Te informamos que se ha realizado una compra por $3.040 con Tarjeta de Credito ****7459 "
                "en EXPRESS PZA DOMINICOS SANTIAGO CL el 04/06/2026 14:56."
            )
        },
    )

    assert outgoing.status_code == 201
    outgoing_candidate = outgoing.json()
    assert Decimal(outgoing_candidate["amount"]) == Decimal("3040.00")
    assert outgoing_candidate["suggested_transaction_type"] == "expense"
    assert outgoing_candidate["cashflow_direction"] == "outflow"
    assert outgoing_candidate["merchant_name"] == "EXPRESS PZA DOMINICOS SANTIAGO CL"
    assert outgoing_candidate["detected_account_type"] == "credit_card"
    assert outgoing_candidate["detected_account_last_four"] == "7459"


def test_import_detects_usd_currency_and_matches_usd_card(client: TestClient) -> None:
    response = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Banco Edwards <avisos@bancoedwards.cl>\n"
                "Subject: Cargo internacional OpenAI\n\n"
                "Te informamos un cargo por US$22.00 con Tarjeta de Credito ****7459 en OPENAI *CHATGPT US.\n"
            )
        },
    )

    assert response.status_code == 201
    candidate = response.json()
    assert Decimal(candidate["amount"]) == Decimal("22.00")
    assert candidate["currency"] == "USD"
    assert candidate["original_currency"] == "USD"
    assert candidate["amount_clp"] is None
    assert candidate["status"] == "needs_review"
    assert candidate["currency_detection_confidence"] >= 0.8
    assert candidate["suggested_financial_account_name"] == "Credito USD · 7459"


def test_import_flags_ambiguous_openai_decimal_as_usd_review(client: TestClient) -> None:
    response = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Banco Demo <avisos@banco.demo>\n"
                "Subject: Cargo tarjeta\n\n"
                "Valor 22.00\n"
                "Comercio OPENAI *CHATGPT US\n"
            )
        },
    )

    assert response.status_code == 201
    candidate = response.json()
    assert Decimal(candidate["amount"]) == Decimal("22.00")
    assert candidate["currency"] == "USD"
    assert candidate["amount_clp"] is None
    assert candidate["status"] == "needs_review"
    assert "internacional" in candidate["currency_detection_reason"].lower()


def test_generic_sender_rule_does_not_flip_received_transfer_to_outflow(client: TestClient) -> None:
    response = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Banco de Chile <avisos@bancochile.cl>\n"
                "Subject: Aviso de transferencia\n\n"
                "Has recibido una transferencia de fondos de Joaquin Ignacio Lagos Sanchez hacia tu cuenta.\n"
                "Monto recibido\t$24.000\n"
                "Fecha de la transferencia\t04/06/2026"
            )
        },
    )

    assert response.status_code == 201
    candidate = response.json()
    assert candidate["suggested_transaction_type"] == "transfer_in"
    assert candidate["cashflow_direction"] == "inflow"
    assert candidate["classification_method"] == "email_parser"


def test_received_transfer_creates_adjustment_for_unassigned_difference(client: TestClient, db_session: Session) -> None:
    person = client.post("/api/v1/people", json={"name": "Diferencia recibida"}).json()
    receivable = client.post(
        "/api/v1/receivables",
        json={
            "person_id": person["id"],
            "title": "Saldo menor",
            "original_amount": "10000.00",
            "currency": "CLP",
            "issued_at": "2026-06-02T12:00:00-04:00",
        },
    ).json()
    preview = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Banco Demo <avisos@banco.demo>\n"
                "Subject: Transferencia recibida $13.000\n\n"
                "Recibiste una transferencia.\n"
                "De: Diferencia recibida\n"
                "Monto: $13.000\n"
            )
        },
    ).json()

    response = client.post(
        "/api/v1/import/confirm",
        json={
            "email_message_id": preview["email_message_id"],
            "import_run_id": preview["import_run_id"],
            "occurred_at": preview["received_at"],
            "amount": preview["amount"],
            "currency": "CLP",
            "counterparty": "Diferencia recibida",
            "person_id": person["id"],
            "category_id": _category_id(client, "Cuentas por cobrar"),
            "transaction_type": "transfer_in",
            "status": "paid",
            "receivable_payments": [{"receivable_id": receivable["id"], "amount": "10000.00"}],
        },
    )

    assert response.status_code == 201
    transaction = response.json()["transaction"]
    assert transaction["transaction_type"] == "receivable_payment"
    assert Decimal(transaction["amount"]) == Decimal("10000.00")

    adjustment = db_session.scalar(select(Transaction).where(Transaction.classification_method == "obligation_adjustment"))
    assert adjustment is not None
    assert adjustment.category.name == "Ingreso por ajuste"
    assert adjustment.amount == Decimal("3000.00")


def test_sent_transfer_can_pay_payable_and_create_cost_adjustment(client: TestClient, db_session: Session) -> None:
    person = client.post("/api/v1/people", json={"name": "Pago enviada"}).json()
    payable = client.post(
        "/api/v1/payables",
        json={
            "person_id": person["id"],
            "title": "Cuota pendiente",
            "original_amount": "9000.00",
            "currency": "CLP",
            "issued_at": "2026-06-02T12:00:00-04:00",
        },
    ).json()
    preview = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Banco Demo <avisos@banco.demo>\n"
                "Subject: Transferencia enviada $12.000\n\n"
                "Enviaste una transferencia.\n"
                "Monto: $12.000\n"
            )
        },
    ).json()

    response = client.post(
        "/api/v1/import/confirm",
        json={
            "email_message_id": preview["email_message_id"],
            "import_run_id": preview["import_run_id"],
            "occurred_at": preview["received_at"],
            "amount": preview["amount"],
            "currency": "CLP",
            "counterparty": "Pago enviada",
            "person_id": person["id"],
            "category_id": _category_id(client, "Cuentas por pagar"),
            "transaction_type": "transfer_out",
            "status": "paid",
            "payable_payments": [{"payable_id": payable["id"], "amount": "9000.00"}],
        },
    )

    assert response.status_code == 201
    transaction = response.json()["transaction"]
    assert transaction["transaction_type"] == "payable_payment"
    assert Decimal(transaction["amount"]) == Decimal("9000.00")

    updated = db_session.scalar(select(Payable).where(Payable.id == payable["id"]))
    assert updated is not None
    assert updated.remaining_amount == Decimal("0.00")
    assert updated.status == "paid"
    adjustment = db_session.scalar(select(Transaction).where(Transaction.classification_method == "obligation_adjustment"))
    assert adjustment is not None
    assert adjustment.category.name == "Costo por ajuste"
    assert adjustment.amount == Decimal("3000.00")


def test_supermarket_internal_receivable_reduces_own_expense(client: TestClient, db_session: Session) -> None:
    person = client.post("/api/v1/people", json={"name": "Roommate"}).json()
    preview = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Banco Demo <avisos@banco.demo>\n"
                "Subject: Compra aprobada Lider por $42.000\n\n"
                "Comercio: Lider\n"
                "Monto: $42.000\n"
            )
        },
    ).json()

    response = client.post(
        "/api/v1/import/confirm",
        json={
            "email_message_id": preview["email_message_id"],
            "import_run_id": preview["import_run_id"],
            "occurred_at": preview["received_at"],
            "amount": preview["amount"],
            "currency": "CLP",
            "merchant_name": "Lider",
            "description": "Compra compartida",
            "category_id": _category_id(client, "Supermercado"),
            "transaction_type": "expense",
            "status": "classified",
            "internal_receivables": [{"person_id": person["id"], "title": "Parte Lider", "amount": "12000.00"}],
        },
    )

    assert response.status_code == 201
    transaction = response.json()["transaction"]
    assert Decimal(transaction["amount"]) == Decimal("30000.00")

    receivable = db_session.scalar(select(Receivable).where(Receivable.person_id == person["id"]))
    assert receivable is not None
    assert receivable.title == "Parte Lider"
    assert receivable.remaining_amount == Decimal("12000.00")


def test_import_internal_payable_reduces_own_income(client: TestClient, db_session: Session) -> None:
    person = client.post("/api/v1/people", json={"name": "Ayudante clase"}).json()
    preview = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Banco Demo <avisos@banco.demo>\n"
                "Subject: Transferencia recibida clase compartida $72.000\n\n"
                "Recibiste una transferencia.\n"
                "De: Alumno Demo\n"
                "Monto: $72.000\n"
                "Motivo: Pago clase matematica."
            )
        },
    ).json()

    response = client.post(
        "/api/v1/import/confirm",
        json={
            "email_message_id": preview["email_message_id"],
            "import_run_id": preview["import_run_id"],
            "occurred_at": preview["received_at"],
            "amount": preview["amount"],
            "currency": "CLP",
            "counterparty": "Alumno Demo",
            "description": "Clase compartida",
            "category_id": _category_id(client, "Clases"),
            "transaction_type": "income",
            "status": "classified",
            "internal_payables": [{"person_id": person["id"], "title": "Parte ayudante", "amount": "12000.00"}],
        },
    )

    assert response.status_code == 201
    transaction = response.json()["transaction"]
    assert Decimal(transaction["amount"]) == Decimal("60000.00")

    payable = db_session.scalar(select(Payable).where(Payable.person_id == person["id"]))
    assert payable is not None
    assert payable.title == "Parte ayudante"
    assert payable.remaining_amount == Decimal("12000.00")


def test_demo_import_returns_candidates_and_can_discard(client: TestClient, db_session: Session) -> None:
    response = client.post("/api/v1/import/demo", json={})

    assert response.status_code == 201
    candidates = response.json()
    assert len(candidates) >= 4
    assert any(candidate["merchant_name"] == "Lider" and candidate["needs_split"] for candidate in candidates)

    discard = client.post(
        "/api/v1/import/discard",
        json={
            "email_message_id": candidates[0]["email_message_id"],
            "import_run_id": candidates[0]["import_run_id"],
        },
    )

    assert discard.status_code == 200
    assert discard.json()["status"] == "discarded"
    email_message = db_session.get(EmailMessage, candidates[0]["email_message_id"])
    assert email_message is not None
    assert email_message.parse_status == "discarded"


def test_import_detects_and_confirms_internal_transfer(client: TestClient, db_session: Session) -> None:
    origin = client.post(
        "/api/v1/financial-accounts",
        json={"name": "Cuenta corriente", "institution": "Banco", "account_type": "checking", "opening_balance": "300000.00"},
    ).json()
    destination = client.post(
        "/api/v1/financial-accounts",
        json={"name": "Cuenta ahorro", "institution": "Banco", "account_type": "savings", "opening_balance": "50000.00"},
    ).json()

    preview = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Banco Demo <avisos@banco.demo>\n"
                "Subject: Traspaso entre tus cuentas por $90.000\n\n"
                "Realizaste un traspaso entre tus cuentas.\n"
                "Monto: $90.000\n"
            )
        },
    ).json()

    assert preview["suggested_transaction_type"] == "internal_transfer"
    assert preview["cashflow_direction"] == "neutral"

    response = client.post(
        "/api/v1/import/confirm",
        json={
            "email_message_id": preview["email_message_id"],
            "import_run_id": preview["import_run_id"],
            "occurred_at": preview["received_at"],
            "amount": preview["amount"],
            "currency": "CLP",
            "subject": preview["subject"],
            "transaction_type": "internal_transfer",
            "status": "classified",
            "financial_account_id": origin["id"],
            "destination_account_id": destination["id"],
        },
    )

    assert response.status_code == 201
    transaction = response.json()["transaction"]
    assert transaction["transaction_type"] == "internal_transfer"
    assert transaction["destination_account"]["id"] == destination["id"]
    assert Decimal(transaction["destination_amount"]) == Decimal("90000.00")
    assert Decimal(transaction["signed_amount"]) == Decimal("-90000")

    dashboard = client.get("/api/v1/dashboard/overview", params={"year": 2026, "month": 6}).json()
    assert Decimal(dashboard["metrics"]["month_expense"]) == Decimal("0")
    assert Decimal(dashboard["metrics"]["month_income"]) == Decimal("0")


def test_import_internal_transfer_requires_destination(client: TestClient) -> None:
    origin = client.post(
        "/api/v1/financial-accounts",
        json={"name": "Cuenta corriente", "institution": "Banco", "account_type": "checking", "opening_balance": "300000.00"},
    ).json()
    preview = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Banco Demo <avisos@banco.demo>\n"
                "Subject: Traspaso entre tus cuentas por $90.000\n\n"
                "Realizaste un traspaso entre tus cuentas.\n"
                "Monto: $90.000\n"
            )
        },
    ).json()

    response = client.post(
        "/api/v1/import/confirm",
        json={
            "email_message_id": preview["email_message_id"],
            "import_run_id": preview["import_run_id"],
            "occurred_at": preview["received_at"],
            "amount": preview["amount"],
            "currency": "CLP",
            "transaction_type": "internal_transfer",
            "status": "classified",
            "financial_account_id": origin["id"],
        },
    )
    assert response.status_code == 400


def test_internal_transfer_detection_survives_generic_bank_rule(client: TestClient) -> None:
    # A broad sender rule maps bancochile.cl to transfer_out, but an explicit
    # own-account transfer must keep its internal_transfer classification.
    preview = client.post(
        "/api/v1/import/text",
        json={
            "raw_text": (
                "From: Banco de Chile <avisos@bancochile.cl>\n"
                "Subject: Traspaso entre tus cuentas por $120.000\n\n"
                "Realizaste un traspaso entre tus cuentas.\n"
                "Monto: $120.000\n"
            )
        },
    ).json()

    assert preview["suggested_transaction_type"] == "internal_transfer"
