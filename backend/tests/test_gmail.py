import base64
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.v1.gmail import _incremental_query, get_gmail_client
from backend.app.models import EmailMessage, GmailSyncState, Transaction
from backend.app.services.gmail_client import (
    GmailAuthenticationError,
    GmailSyncedMessage,
    gmail_message_to_text,
    looks_financial_email,
)


class FakeGmailClient:
    def __init__(self) -> None:
        self.credentials_path = Path("data/local/gmail_credentials.json")
        self.token_path = Path("data/local/gmail_token.json")
        self.scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
        self.settings = SimpleNamespace(
            gmail_redirect_uri="http://127.0.0.1:8000/api/v1/gmail/callback",
            gmail_default_query="newer_than:30d",
        )
        self.connected = True
        self.client_configured = True
        self.disconnected = False
        self.last_label_ids: list[str] = []

    def authorization_url(self) -> str:
        return "https://accounts.google.com/o/oauth2/v2/auth?client_id=fake"

    def disconnect(self) -> None:
        self.connected = False
        self.disconnected = True

    def list_messages(self, *, max_results: int, query: str | None, label_ids: list[str], include_spam_trash: bool = False):
        self.last_label_ids = label_ids
        now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
        inbox_messages = [
            GmailSyncedMessage(
                gmail_message_id="gmail-1",
                gmail_thread_id="thread-1",
                gmail_history_id="hist-1",
                internet_message_id="<gmail-1@example.com>",
                label_id="INBOX",
                received_at=now,
                sender_name="Banco Demo",
                sender_email="avisos@banco.demo",
                subject="Compra aprobada Lider por $42.000",
                raw_text=(
                    "From: Banco Demo <avisos@banco.demo>\n"
                    "Subject: Compra aprobada Lider por $42.000\n"
                    "Snippet: Comercio Lider Monto $42.000"
                ),
                snippet="Comercio Lider Monto $42.000",
                is_financial=True,
                relevance_reason="Palabras financieras y monto detectados",
            ),
            GmailSyncedMessage(
                gmail_message_id="gmail-2",
                gmail_thread_id="thread-2",
                gmail_history_id="hist-2",
                internet_message_id="<gmail-2@example.com>",
                label_id="INBOX",
                received_at=now,
                sender_name="Tienda Demo",
                sender_email="promo@tienda.demo",
                subject="Promocion supermercado sin compra real",
                raw_text="From: Tienda Demo\nSubject: Promocion supermercado sin compra real\nSnippet: descuento semanal",
                snippet="descuento semanal",
                is_financial=False,
                relevance_reason="Sin evidencia financiera suficiente",
            ),
        ]
        spam_messages = [
            GmailSyncedMessage(
                gmail_message_id="gmail-spam-1",
                gmail_thread_id="thread-spam-1",
                gmail_history_id="hist-spam-1",
                internet_message_id="<gmail-spam-1@example.com>",
                label_id="SPAM",
                received_at=now,
                sender_name="Banco Spam Demo",
                sender_email="avisos-spam@banco.demo",
                subject="Compra aprobada Farmacia por $8.500",
                raw_text=(
                    "From: Banco Spam Demo <avisos-spam@banco.demo>\n"
                    "Subject: Compra aprobada Farmacia por $8.500\n"
                    "Comercio: Farmacia\n"
                    "Monto: $8.500"
                ),
                snippet="Comercio Farmacia Monto $8.500",
                is_financial=True,
                relevance_reason="Palabras financieras y monto detectados",
            )
        ]
        requested = set(label_ids or ["INBOX"])
        messages = []
        if "INBOX" in requested:
            messages.extend(inbox_messages)
        if "SPAM" in requested and include_spam_trash:
            messages.extend(spam_messages)
        return (
            messages[:max_results],
            "hist-spam-1" if "SPAM" in requested and include_spam_trash else "hist-2",
        )

    def get_message(self, message_id: str):
        messages, _ = self.list_messages(max_results=10, query=None, label_ids=["INBOX", "SPAM"], include_spam_trash=True)
        return next(message for message in messages if message.gmail_message_id == message_id)


class SingleMessageGmailClient(FakeGmailClient):
    def __init__(self, message: GmailSyncedMessage) -> None:
        super().__init__()
        self.message = message

    def list_messages(self, *, max_results: int, query: str | None, label_ids: list[str], include_spam_trash: bool = False):
        return [self.message], "hist-confirmed"

    def get_message(self, message_id: str):
        return self.message


def _override_gmail(client: TestClient, fake: FakeGmailClient) -> None:
    client.app.dependency_overrides[get_gmail_client] = lambda: fake


def test_incremental_query_overlaps_before_latest_received(db_session: Session) -> None:
    db_session.add(
        EmailMessage(
            gmail_message_id="gmail-latest",
            received_at=datetime(2026, 6, 9, 22, 0, tzinfo=timezone.utc),
            subject="Compra aprobada",
        )
    )
    db_session.commit()

    query = _incremental_query(db_session, "newer_than:30d")

    # Must reach back before the latest day so the day-granular after: filter
    # does not skip same-day or slightly earlier emails (e.g. a Jun 8 purchase).
    assert query == "newer_than:30d after:2026/06/07"


def test_incremental_query_without_history_keeps_base_query(db_session: Session) -> None:
    assert _incremental_query(db_session, "newer_than:30d") == "newer_than:30d"


def test_gmail_status_and_connect_use_local_configuration(client: TestClient) -> None:
    fake = FakeGmailClient()
    _override_gmail(client, fake)

    status_response = client.get("/api/v1/gmail/status")
    connect_response = client.get("/api/v1/gmail/connect")

    assert status_response.status_code == 200
    assert status_response.json()["connected"] is True
    assert status_response.json()["client_configured"] is True
    assert connect_response.status_code == 200
    assert connect_response.json()["authorization_url"].startswith("https://accounts.google.com/")


def test_gmail_sync_imports_candidates_ignores_irrelevant_and_deduplicates(
    client: TestClient,
    db_session: Session,
) -> None:
    fake = FakeGmailClient()
    _override_gmail(client, fake)

    first_response = client.post("/api/v1/gmail/sync", json={"max_results": 10, "label_ids": ["INBOX"]})

    assert first_response.status_code == 201
    first_payload = first_response.json()
    assert first_payload["messages_seen"] == 2
    assert first_payload["ignored_count"] == 1
    assert first_payload["duplicate_count"] == 0
    assert len(first_payload["candidates"]) == 1
    assert first_payload["candidates"][0]["merchant_name"] == "Lider"

    messages = db_session.scalars(select(EmailMessage).order_by(EmailMessage.gmail_message_id)).all()
    assert [message.gmail_message_id for message in messages] == ["gmail-1", "gmail-2"]
    assert [message.parse_status for message in messages] == ["parsed", "discarded"]
    sync_state = db_session.scalar(select(GmailSyncState).where(GmailSyncState.label_id == "INBOX"))
    assert sync_state is not None
    assert sync_state.history_id == "hist-2"

    second_response = client.post("/api/v1/gmail/sync", json={"max_results": 10, "label_ids": ["INBOX"]})

    assert second_response.status_code == 201
    second_payload = second_response.json()
    assert second_payload["duplicate_count"] == 0
    assert second_payload["ignored_count"] == 1
    assert second_payload["reprocessed_count"] == 2
    assert len(second_payload["candidates"]) == 1

    candidates_response = client.get("/api/v1/gmail/candidates")
    assert candidates_response.status_code == 200
    assert len(candidates_response.json()) == 1

    messages_response = client.get("/api/v1/gmail/messages")
    assert messages_response.status_code == 200
    messages_payload = messages_response.json()
    assert [message["subject"] for message in messages_payload[:2]] == [
        "Promocion supermercado sin compra real",
        "Compra aprobada Lider por $42.000",
    ]
    assert [message["parse_status"] for message in messages_payload[:2]] == ["discarded", "parsed"]


def test_gmail_sync_can_read_spam_when_requested(client: TestClient, db_session: Session) -> None:
    fake = FakeGmailClient()
    _override_gmail(client, fake)

    response = client.post(
        "/api/v1/gmail/sync",
        json={"max_results": 10, "label_ids": ["INBOX", "SPAM"], "include_spam_trash": True},
    )

    assert response.status_code == 201
    payload = response.json()
    merchants = {candidate["merchant_name"] for candidate in payload["candidates"]}
    assert "Farmacia" in merchants

    spam_message = db_session.scalar(select(EmailMessage).where(EmailMessage.gmail_message_id == "gmail-spam-1"))
    assert spam_message is not None
    assert spam_message.label_id == "SPAM"
    assert spam_message.parse_status == "parsed"

    spam_state = db_session.scalar(select(GmailSyncState).where(GmailSyncState.label_id == "SPAM"))
    assert spam_state is not None
    assert spam_state.history_id == "hist-spam-1"


def test_gmail_sync_stores_full_body_when_snippet_is_cut(client: TestClient, db_session: Session) -> None:
    now = datetime(2026, 6, 9, 23, 46, tzinfo=timezone.utc)
    body_text = (
        "Persona Demo:\n"
        "Te informamos que se ha realizado una compra por $3.040 con Tarjeta de Credito ****7459 "
        "en EXPRESS PZA DOMINICOS SANTIAGO CL el 09/06/2026 20:46."
    )
    message = GmailSyncedMessage(
        gmail_message_id="gmail-cut-snippet",
        gmail_thread_id="thread-cut-snippet",
        gmail_history_id="hist-cut-snippet",
        internet_message_id="<gmail-cut-snippet@example.com>",
        label_id="INBOX",
        received_at=now,
        sender_name="Banco Edwards",
        sender_email="enviodigital@bancoedwards.cl",
        subject="Compra con Tarjeta de Credito",
        raw_text=(
            "From: Banco Edwards <enviodigital@bancoedwards.cl>\n"
            "Subject: Compra con Tarjeta de Credito\n"
            "Snippet: Persona Demo: Te\n"
            f"{body_text}"
        ),
        snippet="Persona Demo: Te",
        is_financial=True,
        relevance_reason="Palabras financieras y monto detectados",
        body_text=body_text,
    )
    fake = SingleMessageGmailClient(message)
    _override_gmail(client, fake)

    response = client.post("/api/v1/gmail/sync", json={"max_results": 10, "label_ids": ["INBOX"]})

    assert response.status_code == 201
    candidate = response.json()["candidates"][0]
    assert candidate["merchant_name"] == "EXPRESS PZA DOMINICOS SANTIAGO CL"
    assert candidate["detected_account_last_four"] == "7459"
    assert "EXPRESS PZA DOMINICOS" in candidate["body_text"]

    email_message = db_session.scalar(select(EmailMessage).where(EmailMessage.gmail_message_id == "gmail-cut-snippet"))
    assert email_message is not None
    assert email_message.body_text == body_text
    assert "EXPRESS PZA DOMINICOS" in (email_message.body_preview or "")

    messages_response = client.get("/api/v1/gmail/messages")
    assert messages_response.status_code == 200
    assert "EXPRESS PZA DOMINICOS" in messages_response.json()[0]["body_text"]


def test_gmail_sync_reconsiders_discarded_messages_with_full_body(client: TestClient, db_session: Session) -> None:
    now = datetime(2026, 6, 9, 23, 46, tzinfo=timezone.utc)
    body_text = (
        "Persona Demo:\n"
        "Te informamos que se ha realizado una compra por $3.040 con Tarjeta de Credito ****7459 "
        "en EXPRESS PZA DOMINICOS SANTIAGO CL el 09/06/2026 20:46."
    )
    message = GmailSyncedMessage(
        gmail_message_id="gmail-previously-discarded",
        gmail_thread_id="thread-previously-discarded",
        gmail_history_id="hist-previously-discarded",
        internet_message_id="<gmail-previously-discarded@example.com>",
        label_id="INBOX",
        received_at=now,
        sender_name="Banco Edwards",
        sender_email="enviodigital@bancoedwards.cl",
        subject="Compra con Tarjeta de Credito",
        raw_text=(
            "From: Banco Edwards <enviodigital@bancoedwards.cl>\n"
            "Subject: Compra con Tarjeta de Credito\n"
            "Snippet: Persona Demo: Te\n"
            f"{body_text}"
        ),
        snippet="Persona Demo: Te",
        is_financial=True,
        relevance_reason="Palabras financieras y monto detectados",
        body_text=body_text,
    )
    db_session.add(
        EmailMessage(
            gmail_message_id="gmail-previously-discarded",
            received_at=now,
            sender_name="Banco Edwards",
            sender_email="enviodigital@bancoedwards.cl",
            subject="Compra con Tarjeta de Credito",
            body_preview="Persona Demo: Te",
            parse_status="discarded",
        )
    )
    db_session.commit()
    fake = SingleMessageGmailClient(message)
    _override_gmail(client, fake)

    response = client.post("/api/v1/gmail/sync", json={"max_results": 10, "label_ids": ["INBOX"]})

    assert response.status_code == 201
    payload = response.json()
    assert payload["reprocessed_count"] == 1
    assert payload["candidates"][0]["merchant_name"] == "EXPRESS PZA DOMINICOS SANTIAGO CL"
    email_message = db_session.scalar(select(EmailMessage).where(EmailMessage.gmail_message_id == "gmail-previously-discarded"))
    assert email_message is not None
    assert email_message.parse_status == "parsed"
    assert email_message.body_text == body_text


def test_gmail_text_extraction_uses_full_payload_body() -> None:
    body = (
        "Persona Demo:\n"
        "Te informamos que se ha realizado una compra por $3.040 con Tarjeta de Credito ****7459 "
        "en EXPRESS PZA DOMINICOS SANTIAGO CL."
    )
    encoded = base64.urlsafe_b64encode(body.encode("utf-8")).decode("ascii").rstrip("=")
    message = {
        "id": "gmail-full-body",
        "snippet": "Persona Demo: Te",
        "payload": {
            "headers": [
                {"name": "From", "value": "Banco Edwards <enviodigital@bancoedwards.cl>"},
                {"name": "Subject", "value": "Compra con Tarjeta de Credito"},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": encoded},
                }
            ],
        },
    }

    text = gmail_message_to_text(message, include_body=True)
    is_financial, reason = looks_financial_email(text)

    assert "EXPRESS PZA DOMINICOS" in text
    assert "$3.040" in text
    assert is_financial is True
    assert "transaccion" in reason.lower() or "financieras" in reason.lower()


def test_looks_financial_rejects_promotions_that_mention_purchase_and_price() -> None:
    promo = (
        "From: Tienda Demo <promo@tienda.demo>\n"
        "Subject: Cyber imperdible: compra ahora con 50% de descuento\n"
        "Snippet: Ofertas exclusivas\n"
        "Aprovecha nuestras ofertas, productos desde $9.990. Compra ahora y paga en "
        "cuotas sin interes. Suscribete para mas promociones."
    )

    is_financial, reason = looks_financial_email(promo)

    assert is_financial is False
    assert "promocional" in reason.lower()


def test_looks_financial_keeps_transaction_with_promotional_footer() -> None:
    transaction = (
        "From: Banco Edwards <enviodigital@bancoedwards.cl>\n"
        "Subject: Compra con Tarjeta de Credito\n"
        "Te informamos que se ha realizado una compra por $3.040 con Tarjeta de "
        "Credito ****7459 en EXPRESS PZA DOMINICOS.\n"
        "Conoce nuestras ofertas y descuentos exclusivos para ti."
    )

    is_financial, reason = looks_financial_email(transaction)

    assert is_financial is True
    assert "transaccion" in reason.lower()


def test_gmail_text_extraction_prefers_full_html_over_truncated_plain() -> None:
    plain_fallback = "Para ver este correo habilita el contenido HTML."
    html_body = (
        "<html><body><p>Persona Demo:</p>"
        "<p>Te informamos que se ha realizado una compra por <b>$3.040</b> "
        "con Tarjeta de Credito ****7459 en EXPRESS PZA DOMINICOS SANTIAGO CL.</p>"
        "<p>Fecha: 10/06/2026 14:32. Numero de operacion 998877. "
        "Si no reconoces esta compra, comunicate con tu banco.</p></body></html>"
    )
    encoded_plain = base64.urlsafe_b64encode(plain_fallback.encode("utf-8")).decode("ascii").rstrip("=")
    encoded_html = base64.urlsafe_b64encode(html_body.encode("utf-8")).decode("ascii").rstrip("=")
    message = {
        "id": "gmail-alternative",
        "snippet": "Persona Demo: Te",
        "payload": {
            "headers": [
                {"name": "From", "value": "Banco Edwards <enviodigital@bancoedwards.cl>"},
                {"name": "Subject", "value": "Compra con Tarjeta de Credito"},
            ],
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/plain", "body": {"data": encoded_plain}},
                {"mimeType": "text/html", "body": {"data": encoded_html}},
            ],
        },
    }

    text = gmail_message_to_text(message, include_body=True)

    assert "EXPRESS PZA DOMINICOS" in text
    assert "$3.040" in text
    assert "Numero de operacion 998877" in text
    assert "habilita el contenido HTML" not in text


def test_gmail_sync_adds_spam_label_when_include_spam_is_requested(client: TestClient, db_session: Session) -> None:
    fake = FakeGmailClient()
    _override_gmail(client, fake)

    response = client.post(
        "/api/v1/gmail/sync",
        json={"max_results": 10, "label_ids": ["INBOX"], "include_spam_trash": True},
    )

    assert response.status_code == 201
    assert fake.last_label_ids == ["INBOX", "SPAM"]
    spam_message = db_session.scalar(select(EmailMessage).where(EmailMessage.gmail_message_id == "gmail-spam-1"))
    assert spam_message is not None


def test_gmail_visibility_archives_candidates_without_deleting_messages(client: TestClient) -> None:
    fake = FakeGmailClient()
    _override_gmail(client, fake)

    sync_response = client.post("/api/v1/gmail/sync", json={"max_results": 10, "label_ids": ["INBOX"]})
    assert sync_response.status_code == 201
    message_id = sync_response.json()["candidates"][0]["email_message_id"]

    hide_response = client.patch(f"/api/v1/gmail/messages/{message_id}/visibility", json={"is_visible": False})
    assert hide_response.status_code == 200
    assert hide_response.json()["is_visible"] is False

    candidates_response = client.get("/api/v1/gmail/candidates")
    assert candidates_response.status_code == 200
    assert candidates_response.json() == []

    visible_messages_response = client.get("/api/v1/gmail/messages")
    assert visible_messages_response.status_code == 200
    assert message_id not in [message["id"] for message in visible_messages_response.json()]

    archived_response = client.get("/api/v1/gmail/messages", params={"archived_only": True, "visible_only": False})
    assert archived_response.status_code == 200
    archived_messages = archived_response.json()
    assert [message["id"] for message in archived_messages] == [message_id]

    restore_response = client.patch(f"/api/v1/gmail/messages/{message_id}/visibility", json={"is_visible": True})
    assert restore_response.status_code == 200
    assert restore_response.json()["is_visible"] is True


def test_gmail_candidates_survive_unreachable_gmail(client: TestClient) -> None:
    fake = FakeGmailClient()
    _override_gmail(client, fake)

    sync_response = client.post("/api/v1/gmail/sync", json={"max_results": 10, "label_ids": ["INBOX"]})
    assert sync_response.status_code == 201
    assert len(sync_response.json()["candidates"]) == 1

    # Simulate an expired OAuth token: any live Gmail call fails. The pending
    # candidate must still load from the body stored at sync time.
    class FailingGmailClient(FakeGmailClient):
        def get_message(self, message_id: str):
            raise GmailAuthenticationError("token expired")

    _override_gmail(client, FailingGmailClient())

    candidates_response = client.get("/api/v1/gmail/candidates")
    assert candidates_response.status_code == 200
    payload = candidates_response.json()
    assert len(payload) == 1
    assert payload[0]["merchant_name"] == "Lider"


def test_gmail_disconnect_clears_connection_status(client: TestClient) -> None:
    fake = FakeGmailClient()
    _override_gmail(client, fake)

    response = client.post("/api/v1/gmail/disconnect")

    assert response.status_code == 200
    assert response.json()["connected"] is False
    assert fake.disconnected is True


def test_gmail_sync_refreshes_detection_for_confirmed_messages(client: TestClient, db_session: Session) -> None:
    now = datetime(2026, 6, 2, 21, 42, tzinfo=timezone.utc)
    message = GmailSyncedMessage(
        gmail_message_id="gmail-confirmed",
        gmail_thread_id="thread-confirmed",
        gmail_history_id="hist-confirmed",
        internet_message_id="<gmail-confirmed@example.com>",
        label_id="INBOX",
        received_at=now,
        sender_name="Banco Edwards",
        sender_email="enviodigital@bancoedwards.cl",
        subject="Compra con Tarjeta de Crédito",
        raw_text=(
            "From: Banco Edwards <enviodigital@bancoedwards.cl>\n"
            "Subject: Compra con Tarjeta de Crédito\n"
            "Snippet: Compra con Tarjeta de Credito\n"
            "Tarjeta de Credito terminada en **** 9876.\n"
            "Monto: $3.250\n"
        ),
        snippet="ALERTA: Este correo proviene de un remitente externo. Ten cuidado.",
        is_financial=True,
        relevance_reason="Palabras transaccionales detectadas",
    )
    fake = SingleMessageGmailClient(message)
    _override_gmail(client, fake)

    email_message = EmailMessage(
        gmail_message_id="gmail-confirmed",
        received_at=now,
        sender_name="Banco Edwards",
        sender_email="enviodigital@bancoedwards.cl",
        subject="Compra con Tarjeta de Crédito",
        body_preview="ALERTA: Este correo proviene de un remitente externo.",
        parse_status="confirmed",
    )
    db_session.add(email_message)
    db_session.flush()
    transaction = Transaction(
        occurred_at=now,
        amount=Decimal("3250.00"),
        signed_amount=Decimal("-3250.00"),
        currency="CLP",
        transaction_type="expense",
        status="classified",
        source="gmail",
        source_message_id=f"email:{email_message.id}",
    )
    db_session.add(transaction)
    db_session.commit()

    response = client.post("/api/v1/gmail/sync", json={"max_results": 10, "label_ids": ["INBOX"]})

    assert response.status_code == 201
    payload = response.json()
    assert payload["reprocessed_count"] == 1
    db_session.refresh(transaction)
    db_session.refresh(email_message)
    assert transaction.account_detection_method == "email_parser"
    assert transaction.account_detection_reason == "institucion Banco Edwards, tipo credit_card, ultimos digitos 9876"
    assert email_message.parse_status == "confirmed"
    assert not email_message.body_preview.startswith("ALERTA:")
