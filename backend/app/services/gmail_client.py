from __future__ import annotations

import base64
import html
import json
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from backend.app.core.config import PROJECT_ROOT, get_settings


FINANCIAL_KEYWORDS = {
    "abono",
    "aprobada",
    "banco",
    "cargo",
    "clp",
    "compra",
    "comprobante",
    "cuenta",
    "debito",
    "pago",
    "recibiste",
    "tarjeta",
    "transferencia",
}

TRANSACTION_KEYWORDS = {
    "abono",
    "aprobada",
    "cargo",
    "compra",
    "comprobante",
    "debito",
    "pago",
    "recibiste",
    "tarjeta",
    "transferencia",
}

PROMO_KEYWORDS = {
    "black friday",
    "cyber",
    "cuotas sin interes",
    "descuento",
    "dcto",
    "newsletter",
    "oferta",
    "ofertas",
    "promocion",
    "promociones",
    "publicidad",
    "suscribete",
}

SECURITY_KEYWORDS = {
    "alerta de seguridad",
    "dispositivo",
    "inicio de sesion",
    "llave de acceso",
    "nuevo acceso",
}

AMOUNT_PATTERN = re.compile(r"(?:\$|clp|monto|total|compra|abono|transferencia|pago)\s*:?\s*\$?\s*[0-9]", re.IGNORECASE)

# High-precision structures that only appear in real bank/transaction notices:
# masked card numbers, "compra por $...", "abono por $...", explicit "se ha
# realizado" phrasing, etc. Reading the full HTML body surfaces a lot of
# marketing copy, so a concrete signature like this is what separates an actual
# movement from a promotional email that merely mentions "compra" and a price.
TRANSACTION_SIGNATURE = re.compile(
    r"\*{2,}\s*\d{3,4}"  # masked card ****7459
    r"|terminad[ao]\s+en\s+\d{3,4}"  # tarjeta terminada en 7459
    r"|se\s+ha\s+realizado\s+(?:una|un)\b"  # se ha realizado una compra
    r"|(?:compra|abono|cargo|pago|giro|transferencia)\s+(?:nacional\s+|internacional\s+)?(?:por|de)\s*\$?\s*\d"  # compra por $3.040
    r"|recibiste\s+(?:una|un)\s+(?:transferencia|abono|pago)"  # recibiste una transferencia
    r"|transferencia\s+recibida",
)


class GmailConfigurationError(RuntimeError):
    pass


class GmailAuthenticationError(RuntimeError):
    pass


@dataclass(frozen=True)
class GmailSyncedMessage:
    gmail_message_id: str
    gmail_thread_id: str | None
    gmail_history_id: str | None
    internet_message_id: str | None
    label_id: str | None
    received_at: datetime
    sender_name: str | None
    sender_email: str | None
    subject: str
    raw_text: str
    snippet: str
    is_financial: bool
    relevance_reason: str
    body_text: str = ""
    body_html: str | None = None


def _resolve_project_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def _split_scopes(value: str) -> list[str]:
    return [scope.strip() for scope in value.replace(",", " ").split() if scope.strip()]


def looks_financial_email(text: str) -> tuple[bool, str]:
    normalized = _normalize(text)
    has_signature = bool(TRANSACTION_SIGNATURE.search(normalized))
    has_financial_word = any(keyword in normalized for keyword in FINANCIAL_KEYWORDS)
    has_transaction_word = any(keyword in normalized for keyword in TRANSACTION_KEYWORDS)
    has_amount = bool(AMOUNT_PATTERN.search(normalized))
    has_promo_word = any(keyword in normalized for keyword in PROMO_KEYWORDS)
    has_security_word = any(keyword in normalized for keyword in SECURITY_KEYWORDS)

    # A concrete transaction signature is high precision, so trust it even when
    # the email also carries a promotional footer.
    if has_signature:
        return True, "Estructura de transaccion detectada"

    if has_security_word and not has_transaction_word:
        return False, "Correo de seguridad sin transaccion"

    # Promotions routinely borrow transactional words ("compra ahora", "paga en
    # cuotas") and list prices. Without a transaction signature, any promotional
    # signal wins so marketing copy in the full body does not leak through.
    if has_promo_word:
        return False, "Correo promocional sin transaccion"

    if has_transaction_word and has_amount:
        return True, "Palabras financieras y monto detectados"
    if has_transaction_word:
        return True, "Palabras transaccionales detectadas"
    if has_financial_word and has_amount:
        return True, "Palabras financieras sin senal promocional fuerte"
    return False, "Sin evidencia financiera suficiente"


class GmailClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.credentials_path = _resolve_project_path(self.settings.gmail_credentials_path)
        self.token_path = _resolve_project_path(self.settings.gmail_token_path)
        self.oauth_state_path = self.token_path.with_name("gmail_oauth_pending.json")
        self.scopes = _split_scopes(self.settings.gmail_scopes)

    @property
    def client_configured(self) -> bool:
        return self.credentials_path.exists()

    @property
    def connected(self) -> bool:
        return self.token_path.exists()

    def authorization_url(self) -> str:
        flow = self._build_flow()
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        self._save_pending_oauth_state(state, flow.code_verifier)
        return authorization_url

    def handle_callback(self, code: str, state: str | None) -> None:
        pending_state = self._load_pending_oauth_state()
        expected_state = pending_state.get("state")
        if expected_state and state != expected_state:
            raise GmailAuthenticationError("Gmail OAuth state mismatch; reconnect Gmail")

        flow = self._build_flow(
            state=expected_state,
            code_verifier=pending_state.get("code_verifier"),
            autogenerate_code_verifier=False,
        )
        try:
            flow.fetch_token(code=code)
        except Exception as exc:
            raise GmailAuthenticationError(f"Google OAuth token exchange failed: {exc}") from exc
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(flow.credentials.to_json(), encoding="utf-8")
        self._clear_pending_oauth_state()

    def disconnect(self) -> None:
        if self.token_path.exists():
            self.token_path.unlink()

    def list_messages(
        self,
        *,
        max_results: int,
        query: str | None,
        label_ids: list[str],
        include_spam_trash: bool = False,
    ) -> tuple[list[GmailSyncedMessage], str | None]:
        service = self._build_service()
        message_refs_by_id: dict[str, dict[str, Any]] = {}
        labels_to_fetch = label_ids or [None]
        for label_id in labels_to_fetch:
            request = service.users().messages().list(
                userId="me",
                maxResults=max_results,
                q=query,
                labelIds=[label_id] if label_id else None,
                includeSpamTrash=include_spam_trash or label_id == "SPAM",
            )
            response = request.execute()
            for message_ref in response.get("messages", []):
                message_refs_by_id.setdefault(message_ref["id"], message_ref)
        message_refs = list(message_refs_by_id.values())
        profile = service.users().getProfile(userId="me").execute()
        current_history_id = profile.get("historyId")
        messages: list[GmailSyncedMessage] = []

        for message_ref in message_refs:
            message = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=message_ref["id"],
                    format="full",
                )
                .execute()
            )
            raw_text = gmail_message_to_text(message, include_body=True)
            is_financial, reason = looks_financial_email(raw_text)
            messages.append(_to_synced_message(message, raw_text, is_financial, reason))

        return messages, current_history_id

    def get_message(self, message_id: str) -> GmailSyncedMessage:
        service = self._build_service()
        message = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        raw_text = gmail_message_to_text(message, include_body=True)
        is_financial, reason = looks_financial_email(raw_text)
        return _to_synced_message(message, raw_text, is_financial, reason)

    def _build_flow(
        self,
        *,
        state: str | None = None,
        code_verifier: str | None = None,
        autogenerate_code_verifier: bool = True,
    ):
        if not self.client_configured:
            raise GmailConfigurationError(f"Gmail credentials file not found: {self.credentials_path}")
        try:
            from google_auth_oauthlib.flow import Flow
        except ImportError as exc:
            raise GmailConfigurationError("Google OAuth dependencies are not installed") from exc

        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
        return Flow.from_client_secrets_file(
            str(self.credentials_path),
            scopes=self.scopes,
            redirect_uri=self.settings.gmail_redirect_uri,
            state=state,
            code_verifier=code_verifier,
            autogenerate_code_verifier=autogenerate_code_verifier,
        )

    def _build_service(self):
        if not self.connected:
            raise GmailAuthenticationError("Gmail is not connected")
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise GmailConfigurationError("Google Gmail dependencies are not installed") from exc

        credentials = Credentials.from_authorized_user_file(str(self.token_path), self.scopes)
        if not credentials.valid:
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                self.token_path.write_text(credentials.to_json(), encoding="utf-8")
            else:
                raise GmailAuthenticationError("Gmail token is expired or invalid; reconnect Gmail")
        return build("gmail", "v1", credentials=credentials, cache_discovery=False)

    def _save_pending_oauth_state(self, state: str | None, code_verifier: str | None) -> None:
        if not state or not code_verifier:
            raise GmailAuthenticationError("Google OAuth did not return state or code verifier")
        self.oauth_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.oauth_state_path.write_text(
            json.dumps(
                {
                    "state": state,
                    "code_verifier": code_verifier,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ),
            encoding="utf-8",
        )

    def _load_pending_oauth_state(self) -> dict[str, str]:
        if not self.oauth_state_path.exists():
            raise GmailAuthenticationError("Missing pending Gmail OAuth state; click Conectar Gmail again")
        try:
            data = json.loads(self.oauth_state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise GmailAuthenticationError("Pending Gmail OAuth state is invalid; reconnect Gmail") from exc
        return {key: str(value) for key, value in data.items() if value is not None}

    def _clear_pending_oauth_state(self) -> None:
        if self.oauth_state_path.exists():
            self.oauth_state_path.unlink()


def gmail_message_to_text(message: dict[str, Any], include_body: bool) -> str:
    headers = _headers(message)
    lines = [
        f"From: {headers.get('from', '')}",
        f"Subject: {headers.get('subject', '(sin asunto)')}",
    ]
    if headers.get("date"):
        lines.append(f"Date: {headers['date']}")
    if message.get("snippet"):
        lines.append(f"Snippet: {message['snippet']}")
    if include_body:
        body_text, _ = _extract_body_parts(message.get("payload", {}))
        if body_text:
            lines.append(body_text)
    return "\n".join(line for line in lines if line.strip())


def _to_synced_message(message: dict[str, Any], raw_text: str, is_financial: bool, reason: str) -> GmailSyncedMessage:
    headers = _headers(message)
    sender_name, sender_email = _parse_sender(headers.get("from"))
    received_at = _received_at(message, headers)
    label_ids = message.get("labelIds") or []
    body_text, body_html = _extract_body_parts(message.get("payload", {}))
    return GmailSyncedMessage(
        gmail_message_id=message["id"],
        gmail_thread_id=message.get("threadId"),
        gmail_history_id=message.get("historyId"),
        internet_message_id=headers.get("message-id"),
        label_id=next(iter(label_ids), None),
        received_at=received_at,
        sender_name=sender_name,
        sender_email=sender_email,
        subject=headers.get("subject") or "(sin asunto)",
        raw_text=raw_text,
        snippet=message.get("snippet") or "",
        is_financial=is_financial,
        relevance_reason=reason,
        body_text=body_text,
        body_html=body_html,
    )


def _headers(message: dict[str, Any]) -> dict[str, str]:
    payload = message.get("payload") or {}
    headers = payload.get("headers") or []
    return {header.get("name", "").lower(): header.get("value", "") for header in headers}


def _extract_body_parts(part: dict[str, Any]) -> tuple[str, str | None]:
    plain_parts: list[str] = []
    html_parts: list[str] = []
    _collect_body_parts(part, plain_parts, html_parts)
    body_html = "\n".join(part for part in html_parts if part.strip()).strip() or None
    plain_text = "\n\n".join(part for part in plain_parts if part.strip()).strip()
    html_text = _html_to_text(body_html) if body_html else ""
    # Bank notifications are usually multipart/alternative: a short text/plain
    # fallback next to the complete text/html body. Keep whichever version
    # carries more content so we store the full email instead of the truncated
    # alternative.
    body_text = plain_text if len(plain_text) >= len(html_text) else html_text
    return body_text, body_html


def _collect_body_parts(part: dict[str, Any], plain_parts: list[str], html_parts: list[str]) -> None:
    parts = part.get("parts") or []
    if parts:
        for child in parts:
            _collect_body_parts(child, plain_parts, html_parts)
        return

    mime_type = part.get("mimeType", "")
    if mime_type not in {"text/plain", "text/html"}:
        return
    data = (part.get("body") or {}).get("data")
    if not data:
        return
    decoded = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="ignore")
    if mime_type == "text/html":
        html_parts.append(decoded.strip())
    else:
        plain_parts.append(decoded.strip())


def _html_to_text(value: str) -> str:
    without_scripts = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    with_breaks = re.sub(r"</?(?:br|p|div|tr|table|li|h[1-6])\b[^>]*>", "\n", without_scripts, flags=re.IGNORECASE)
    without_tags = re.sub(r"<[^>]+>", " ", with_breaks)
    unescaped = html.unescape(without_tags)
    lines = [" ".join(line.split()) for line in unescaped.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _received_at(message: dict[str, Any], headers: dict[str, str]) -> datetime:
    internal_date = message.get("internalDate")
    if internal_date:
        return datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)
    if headers.get("date"):
        try:
            parsed = parsedate_to_datetime(headers["date"])
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    return datetime.now(timezone.utc)


def _parse_sender(sender: str | None) -> tuple[str | None, str | None]:
    if not sender:
        return None, None
    match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", sender)
    email = match.group(0) if match else None
    name = sender.replace(email or "", "").replace("<", "").replace(">", "").strip().strip('"') or None
    return name, email


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(char for char in decomposed if not unicodedata.combining(char))
    return ascii_value.lower()
