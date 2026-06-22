from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.schemas.importing import ImportCandidateRead


class GmailStatus(BaseModel):
    connected: bool
    client_configured: bool
    credentials_path: str
    token_path: str
    redirect_uri: str
    scopes: list[str]
    default_query: str
    last_sync_at: datetime | None = None
    last_history_id: str | None = None


class GmailConnectResponse(BaseModel):
    authorization_url: str
    redirect_uri: str
    scopes: list[str]


class GmailSyncRequest(BaseModel):
    max_results: int = Field(default=5, ge=1, le=50)
    query: str | None = None
    label_ids: list[str] = Field(default_factory=lambda: ["INBOX"])
    include_spam_trash: bool = False


class GmailSyncResponse(BaseModel):
    import_run_id: int
    candidates: list[ImportCandidateRead] = Field(default_factory=list)
    ignored_count: int = 0
    duplicate_count: int = 0
    parse_error_count: int = 0
    reprocessed_count: int = 0
    messages_seen: int = 0
    history_id: str | None = None


class GmailMessageRead(BaseModel):
    id: int
    gmail_message_id: str | None = None
    received_at: datetime
    sender_name: str | None = None
    sender_email: str | None = None
    subject: str
    body_preview: str | None = None
    body_text: str | None = None
    body_html: str | None = None
    parse_status: str
    is_visible: bool = True
    import_run_id: int | None = None


class GmailMessageVisibilityUpdate(BaseModel):
    is_visible: bool


class GmailDisconnectResponse(BaseModel):
    connected: bool
