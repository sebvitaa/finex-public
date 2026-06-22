import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.models import EmailMessage, GmailSyncState, ImportRun, Transaction
from backend.app.schemas import (
    GmailConnectResponse,
    GmailDisconnectResponse,
    GmailMessageRead,
    GmailMessageVisibilityUpdate,
    GmailStatus,
    GmailSyncRequest,
    GmailSyncResponse,
    ImportCandidateRead,
)
from backend.app.services.email_parser import EmailParseError, ParsedEmailCandidate, body_hash, parse_email_text
from backend.app.services.gmail_client import (
    GmailAuthenticationError,
    GmailClient,
    GmailConfigurationError,
    GmailSyncedMessage,
)
from backend.app.api.v1.imports import _create_import_run, _match_financial_account, _to_candidate_response


router = APIRouter(prefix="/gmail", tags=["gmail"])

# Days of overlap when building the incremental Gmail query so day-granular
# after: filtering does not silently skip same-day or late-arriving emails.
INCREMENTAL_OVERLAP_DAYS = 2

EXTERNAL_WARNING_RE = re.compile(
    r"alerta:\s*este correo proviene de un remitente externo\..*?no los abras a menos que est[ée]s seguro\.\s*",
    re.IGNORECASE | re.DOTALL,
)


def get_gmail_client() -> GmailClient:
    return GmailClient()


@router.get("/status", response_model=GmailStatus)
def gmail_status(
    gmail_client: GmailClient = Depends(get_gmail_client),
    db: Session = Depends(get_db),
) -> GmailStatus:
    latest_state = db.scalar(select(GmailSyncState).order_by(GmailSyncState.last_sync_at.desc().nullslast()))
    return GmailStatus(
        connected=gmail_client.connected,
        client_configured=gmail_client.client_configured,
        credentials_path=str(gmail_client.credentials_path),
        token_path=str(gmail_client.token_path),
        redirect_uri=gmail_client.settings.gmail_redirect_uri,
        scopes=gmail_client.scopes,
        default_query=gmail_client.settings.gmail_default_query,
        last_sync_at=latest_state.last_sync_at if latest_state else None,
        last_history_id=latest_state.history_id if latest_state else None,
    )


@router.get("/connect", response_model=GmailConnectResponse)
def gmail_connect(gmail_client: GmailClient = Depends(get_gmail_client)) -> GmailConnectResponse:
    try:
        authorization_url = gmail_client.authorization_url()
    except GmailConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return GmailConnectResponse(
        authorization_url=authorization_url,
        redirect_uri=gmail_client.settings.gmail_redirect_uri,
        scopes=gmail_client.scopes,
    )


@router.get("/callback", response_class=HTMLResponse)
def gmail_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    gmail_client: GmailClient = Depends(get_gmail_client),
) -> HTMLResponse:
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Gmail OAuth code")
    try:
        gmail_client.handle_callback(code, state)
    except (GmailConfigurationError, GmailAuthenticationError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return HTMLResponse(
        """
        <html>
          <body style="font-family: system-ui; background: #050505; color: #f4f4f5; padding: 32px;">
            <h1>Gmail conectado</h1>
            <p>Ya puedes volver a FinEx y usar Actualizar Gmail.</p>
          </body>
        </html>
        """
    )


@router.post("/sync", response_model=GmailSyncResponse, status_code=status.HTTP_201_CREATED)
def gmail_sync(
    payload: GmailSyncRequest,
    gmail_client: GmailClient = Depends(get_gmail_client),
    db: Session = Depends(get_db),
) -> GmailSyncResponse:
    import_run = _create_import_run(db, "gmail", messages_seen=0)
    query = payload.query if payload.query is not None else _incremental_query(db, gmail_client.settings.gmail_default_query)
    label_ids = _sync_label_ids(payload.label_ids, payload.include_spam_trash)

    try:
        messages, history_id = gmail_client.list_messages(
            max_results=payload.max_results,
            query=query,
            label_ids=label_ids,
            include_spam_trash=payload.include_spam_trash,
        )
    except GmailAuthenticationError as exc:
        import_run.status = "failed"
        import_run.errors_count = 1
        import_run.error_summary = str(exc)
        db.add(import_run)
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except GmailConfigurationError as exc:
        import_run.status = "failed"
        import_run.errors_count = 1
        import_run.error_summary = str(exc)
        db.add(import_run)
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    import_run.messages_seen = len(messages)
    candidates = []
    ignored_count = 0
    duplicate_count = 0
    parse_error_count = 0
    reprocessed_count = 0

    for message in messages:
        existing_message = db.scalar(select(EmailMessage).where(EmailMessage.gmail_message_id == message.gmail_message_id))
        if existing_message is not None:
            if not existing_message.is_visible:
                duplicate_count += 1
                continue

            if existing_message.parse_status == "parsed":
                try:
                    parsed = parse_email_text(message.raw_text, received_at=message.received_at)
                except EmailParseError as exc:
                    parse_error_count += 1
                    import_run.errors_count += 1
                    import_run.error_summary = str(exc)
                    _refresh_gmail_email_message(existing_message, message, import_run.id, parse_status="parse_failed")
                    db.add(existing_message)
                    continue

                _refresh_gmail_email_message(existing_message, message, import_run.id, parse_status="parsed")
                reprocessed_count += 1
                candidates.append(_to_candidate_response(parsed, existing_message, import_run, db))
                continue

            if existing_message.parse_status == "parse_failed":
                if not message.is_financial:
                    _refresh_gmail_email_message(existing_message, message, import_run.id, parse_status="discarded")
                    ignored_count += 1
                    reprocessed_count += 1
                    continue

                try:
                    parsed = parse_email_text(message.raw_text, received_at=message.received_at)
                except EmailParseError as exc:
                    parse_error_count += 1
                    import_run.errors_count += 1
                    import_run.error_summary = str(exc)
                    _refresh_gmail_email_message(existing_message, message, import_run.id, parse_status="parse_failed")
                    db.add(existing_message)
                    continue

                _refresh_gmail_email_message(existing_message, message, import_run.id, parse_status="parsed")
                import_run.messages_imported += 1
                reprocessed_count += 1
                candidates.append(_to_candidate_response(parsed, existing_message, import_run, db))
                continue

            if existing_message.parse_status == "discarded":
                if not message.is_financial:
                    _refresh_gmail_email_message(existing_message, message, import_run.id, parse_status="discarded")
                    ignored_count += 1
                    reprocessed_count += 1
                    continue

                try:
                    parsed = parse_email_text(message.raw_text, received_at=message.received_at)
                except EmailParseError as exc:
                    parse_error_count += 1
                    import_run.errors_count += 1
                    import_run.error_summary = str(exc)
                    _refresh_gmail_email_message(existing_message, message, import_run.id, parse_status="parse_failed")
                    db.add(existing_message)
                    continue

                _refresh_gmail_email_message(existing_message, message, import_run.id, parse_status="parsed")
                import_run.messages_imported += 1
                reprocessed_count += 1
                candidates.append(_to_candidate_response(parsed, existing_message, import_run, db))
                continue

            if existing_message.parse_status == "confirmed":
                if message.is_financial:
                    try:
                        parsed = parse_email_text(message.raw_text, received_at=message.received_at)
                    except EmailParseError:
                        duplicate_count += 1
                        continue

                    _refresh_gmail_email_message(existing_message, message, import_run.id, parse_status="confirmed")
                    if _refresh_confirmed_transaction_detection(parsed, existing_message, db):
                        reprocessed_count += 1
                    else:
                        duplicate_count += 1
                    db.add(existing_message)
                    continue

            duplicate_count += 1
            continue
        if not message.is_financial:
            _create_gmail_email_message(db, message, import_run.id, parse_status="discarded")
            ignored_count += 1
            continue
        try:
            parsed = parse_email_text(message.raw_text, received_at=message.received_at)
        except EmailParseError as exc:
            _create_gmail_email_message(db, message, import_run.id, parse_status="parse_failed")
            parse_error_count += 1
            import_run.errors_count += 1
            import_run.error_summary = str(exc)
            continue

        email_message = _create_gmail_email_message(db, message, import_run.id, parse_status="parsed")
        import_run.messages_imported += 1
        candidates.append(_to_candidate_response(parsed, email_message, import_run, db))

    _update_sync_state(db, label_ids, history_id)
    import_run.finished_at = datetime.now(timezone.utc)
    import_run.status = "previewed" if candidates else "no_candidates"
    db.add(import_run)
    db.commit()

    return GmailSyncResponse(
        import_run_id=import_run.id,
        candidates=candidates,
        ignored_count=ignored_count,
        duplicate_count=duplicate_count,
        parse_error_count=parse_error_count,
        reprocessed_count=reprocessed_count,
        messages_seen=import_run.messages_seen,
        history_id=history_id,
    )


def _sync_label_ids(label_ids: list[str], include_spam_trash: bool) -> list[str]:
    labels = list(dict.fromkeys(label_ids or ["INBOX"]))
    if include_spam_trash and "SPAM" not in labels:
        labels.append("SPAM")
    return labels


@router.get("/candidates", response_model=list[ImportCandidateRead])
def gmail_candidates(
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[ImportCandidateRead]:
    email_messages = db.scalars(
        select(EmailMessage)
        .where(
            EmailMessage.gmail_message_id.is_not(None),
            EmailMessage.parse_status == "parsed",
            EmailMessage.is_visible.is_(True),
        )
        .order_by(EmailMessage.received_at.desc(), EmailMessage.id.desc())
        .limit(limit)
    ).all()

    # Rebuild candidates from the body already stored at sync time instead of
    # re-fetching each message from Gmail. The pending list must stay available
    # even when the OAuth token expired or Gmail is briefly unreachable; a single
    # live round-trip failure used to wipe every pending candidate at once.
    candidates = []
    for email_message in email_messages:
        if not email_message.gmail_message_id:
            continue
        import_run = db.get(ImportRun, email_message.import_run_id) if email_message.import_run_id else _create_import_run(db, "gmail", 0)
        try:
            parsed = parse_email_text(
                _email_message_raw_text(email_message),
                received_at=email_message.received_at,
            )
        except EmailParseError:
            email_message.parse_status = "parse_failed"
            db.add(email_message)
            continue

        candidates.append(_to_candidate_response(parsed, email_message, import_run, db))

    db.commit()
    return candidates


@router.get("/messages", response_model=list[GmailMessageRead])
def gmail_messages(
    limit: int = Query(default=20, ge=1, le=50),
    visible_only: bool = Query(default=True),
    archived_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[GmailMessageRead]:
    query = select(EmailMessage).where(EmailMessage.gmail_message_id.is_not(None))
    if archived_only:
        query = query.where(EmailMessage.is_visible.is_(False))
    elif visible_only:
        query = query.where(EmailMessage.is_visible.is_(True))
    messages = db.scalars(query.order_by(EmailMessage.received_at.desc(), EmailMessage.id.desc()).limit(limit)).all()
    return [_to_gmail_message_read(message) for message in messages]


@router.patch("/messages/{message_id}/visibility", response_model=GmailMessageRead)
def gmail_message_visibility(
    message_id: int,
    payload: GmailMessageVisibilityUpdate,
    db: Session = Depends(get_db),
) -> GmailMessageRead:
    message = db.get(EmailMessage, message_id)
    if message is None or message.gmail_message_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gmail message not found")
    message.is_visible = payload.is_visible
    db.add(message)
    db.commit()
    db.refresh(message)
    return _to_gmail_message_read(message)


@router.post("/disconnect", response_model=GmailDisconnectResponse)
def gmail_disconnect(gmail_client: GmailClient = Depends(get_gmail_client)) -> GmailDisconnectResponse:
    gmail_client.disconnect()
    return GmailDisconnectResponse(connected=gmail_client.connected)


def _create_gmail_email_message(
    db: Session,
    message: GmailSyncedMessage,
    import_run_id: int,
    parse_status: str,
) -> EmailMessage:
    email_message = EmailMessage(
        gmail_message_id=message.gmail_message_id,
        gmail_thread_id=message.gmail_thread_id,
        gmail_history_id=message.gmail_history_id,
        internet_message_id=message.internet_message_id,
        received_at=message.received_at,
        sender_name=message.sender_name,
        sender_email=message.sender_email,
        subject=message.subject[:240],
        body_preview=_message_preview(message),
        body_text=message.body_text or message.raw_text,
        body_html=message.body_html,
        body_hash=body_hash(message.raw_text),
        label_id=message.label_id,
        import_run_id=import_run_id,
        parse_status=parse_status,
    )
    db.add(email_message)
    db.flush()
    return email_message


def _email_message_raw_text(email_message: EmailMessage) -> str:
    sender = email_message.sender_email or ""
    if email_message.sender_name:
        sender = f"{email_message.sender_name} <{sender}>".strip()
    header_lines = []
    if sender:
        header_lines.append(f"From: {sender}")
    if email_message.subject:
        header_lines.append(f"Subject: {email_message.subject}")
    body = email_message.body_text or email_message.body_preview or ""
    return "\n".join([*header_lines, "", body])


def _to_gmail_message_read(message: EmailMessage) -> GmailMessageRead:
    return GmailMessageRead(
        id=message.id,
        gmail_message_id=message.gmail_message_id,
        received_at=message.received_at,
        sender_name=message.sender_name,
        sender_email=message.sender_email,
        subject=message.subject,
        body_preview=message.body_preview,
        body_text=message.body_text,
        body_html=message.body_html,
        parse_status=message.parse_status,
        is_visible=message.is_visible,
        import_run_id=message.import_run_id,
    )


def _refresh_gmail_email_message(
    email_message: EmailMessage,
    message: GmailSyncedMessage,
    import_run_id: int,
    parse_status: str,
) -> EmailMessage:
    email_message.gmail_thread_id = message.gmail_thread_id
    email_message.gmail_history_id = message.gmail_history_id
    email_message.internet_message_id = message.internet_message_id
    email_message.received_at = message.received_at
    email_message.sender_name = message.sender_name
    email_message.sender_email = message.sender_email
    email_message.subject = message.subject[:240]
    email_message.body_preview = _message_preview(message)
    email_message.body_text = message.body_text or message.raw_text
    email_message.body_html = message.body_html
    email_message.body_hash = body_hash(message.raw_text)
    email_message.label_id = message.label_id
    email_message.import_run_id = import_run_id
    email_message.parse_status = parse_status
    return email_message


def _message_preview(message: GmailSyncedMessage) -> str | None:
    body_preview = _clean_preview(message.body_text or message.raw_text)
    snippet = _clean_preview(message.snippet)
    return (body_preview or snippet or None)[:500] if body_preview or snippet else None


def _clean_preview(value: str | None) -> str:
    if not value:
        return ""
    collapsed = " ".join(value.split())
    without_warning = EXTERNAL_WARNING_RE.sub("", collapsed)
    return without_warning.strip()


def _refresh_confirmed_transaction_detection(
    parsed: ParsedEmailCandidate,
    email_message: EmailMessage,
    db: Session,
) -> bool:
    transaction = db.scalar(select(Transaction).where(Transaction.source_message_id == f"email:{email_message.id}"))
    if transaction is None:
        return False

    changed = False
    account = _match_financial_account(parsed, db)
    if transaction.financial_account_id is None and account is not None:
        transaction.financial_account_id = account.id
        changed = True

    if parsed.account_detection_reason and transaction.account_detection_reason != parsed.account_detection_reason:
        transaction.account_detection_method = "email_parser"
        transaction.account_detection_confidence = parsed.account_detection_confidence
        transaction.account_detection_reason = parsed.account_detection_reason
        changed = True

    if changed:
        db.add(transaction)
    return changed


def _update_sync_state(db: Session, label_ids: list[str], history_id: str | None) -> None:
    now = datetime.now(timezone.utc)
    labels = label_ids or ["ALL"]
    for label_id in labels:
        state = db.scalar(select(GmailSyncState).where(GmailSyncState.label_id == label_id))
        if state is None:
            state = GmailSyncState(label_id=label_id, history_id=history_id, last_sync_at=now)
        else:
            state.history_id = history_id or state.history_id
            state.last_sync_at = now
        db.add(state)


def _incremental_query(db: Session, default_query: str | None) -> str | None:
    latest = db.scalar(
        select(EmailMessage.received_at)
        .where(EmailMessage.gmail_message_id.is_not(None))
        .order_by(EmailMessage.received_at.desc(), EmailMessage.id.desc())
        .limit(1)
    )
    base_query = (default_query or "").strip()
    if latest is None or any(token in base_query.lower() for token in ("after:", "before:")):
        return base_query or None
    # Gmail's after: operator is day-granular and excludes anything earlier than
    # that calendar day (in the account timezone). Anchoring exactly on the
    # latest received date silently drops same-day or slightly older emails that
    # were never captured (e.g. late-arriving bank notices or messages beyond the
    # max_results window). Overlap a few days back so they are still fetched;
    # re-seen messages are cheaply deduplicated by gmail_message_id.
    overlap_floor = latest - timedelta(days=INCREMENTAL_OVERLAP_DAYS)
    return f"{base_query} after:{overlap_floor:%Y/%m/%d}".strip()
