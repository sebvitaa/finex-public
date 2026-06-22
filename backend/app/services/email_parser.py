from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class ParsedSplit:
    category_name: str
    amount: Decimal
    label: str


@dataclass(frozen=True)
class ParsedEmailCandidate:
    subject: str
    body_preview: str
    body_text: str
    body_hash: str
    received_at: datetime
    sender_name: str | None
    sender_email: str | None
    amount: Decimal
    currency: str
    original_amount: Decimal
    original_currency: str
    amount_clp: Decimal | None
    exchange_rate: Decimal | None
    exchange_rate_source: str | None
    exchange_rate_date: datetime | None
    currency_detection_confidence: float
    currency_detection_reason: str
    merchant_name: str | None
    counterparty: str | None
    description: str
    suggested_category_name: str
    suggested_transaction_type: str
    cashflow_direction: str
    status: str
    confidence: float
    classification_reason: str
    needs_split: bool
    detected_account_institution: str | None = None
    detected_account_type: str | None = None
    detected_account_last_four: str | None = None
    account_detection_confidence: float | None = None
    account_detection_reason: str | None = None
    suggested_splits: list[ParsedSplit] = field(default_factory=list)


@dataclass(frozen=True)
class DetectedMoney:
    amount: Decimal
    currency: str
    original_amount: Decimal
    original_currency: str
    amount_clp: Decimal | None
    exchange_rate: Decimal | None
    exchange_rate_source: str | None
    exchange_rate_date: datetime | None
    confidence: float
    reason: str


MERCHANT_KEYWORDS = {
    "lider": "Lider",
    "jumbo": "Jumbo",
    "unimarc": "Unimarc",
    "tottus": "Tottus",
    "santa isabel": "Santa Isabel",
    "rappi": "Rappi",
    "pedidosya": "PedidosYa",
    "uber": "Uber",
    "cabify": "Cabify",
    "spotify": "Spotify",
    "netflix": "Netflix",
    "youtube": "YouTube",
    "icloud": "iCloud",
    "mercado pago": "Mercado Pago",
    "mercadolibre": "Mercado Libre",
    "amazon": "Amazon",
}

SUPERMARKETS = {"Lider", "Jumbo", "Unimarc", "Tottus", "Santa Isabel"}
SUBSCRIPTIONS = {"Spotify", "Netflix", "YouTube", "iCloud"}
DELIVERY = {"Rappi", "PedidosYa"}
ONLINE_SHOPS = {"Mercado Pago", "Mercado Libre", "Amazon"}

FOOD_WORDS = {"pan", "leche", "arroz", "pollo", "huevo", "huevos", "fruta", "verdura", "queso", "yogurt"}
SNACK_WORDS = {"chocolate", "galleta", "galletas", "bebida", "snack", "dulce", "helado", "papas"}
CLEANING_WORDS = {"detergente", "cloro", "lavalozas", "papel higienico", "servilleta", "limpieza"}

INSTITUTION_ALIASES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("bancoedwards", "banco edwards", "edwards citi", "edwards"), "Banco Edwards"),
    (("bancochile", "banco de chile", "banco chile"), "Banco de Chile"),
    (("banco estado", "bancoestado"), "BancoEstado"),
    (("santander",), "Santander"),
    (("banco bci", "bci.cl", " bci ", "bci"), "BCI"),
    (("itau",), "Itau"),
    (("scotiabank", "scotia"), "Scotiabank"),
    (("banco falabella", "falabella", "cmr"), "Banco Falabella"),
    (("banco ripley", "ripley"), "Banco Ripley"),
    (("banco security", "bancosecurity", "security"), "Banco Security"),
    (("banco bice", "bice"), "Banco BICE"),
    (("mach",), "MACH"),
    (("tenpo",), "Tenpo"),
    (("mercado pago", "mercadopago"), "Mercado Pago"),
    (("fintual",), "Fintual"),
    (("racional",), "Racional"),
)

LAST_FOUR_PATTERNS = (
    r"(?:terminad[ao]|finalizad[ao])\s+en\s+(?:[*x\-\s.]*)(\d{4})\b",
    r"(?:ultimos?\s+(?:4\s+)?digitos?|digitos?\s+finales?)\D{0,24}(\d{4})\b",
    r"(?:tarjeta|cuenta|cta|producto|nro\.?|numero|num\.?|no\.?)\D{0,36}(?:[*x\-\s.]{2,})\D{0,12}(\d{4})\b",
    r"(?:[*x]{2,}[\s.-]*){2,}(\d{4})\b",
    r"\b(?:visa|mastercard|amex|redcompra)\D{0,28}(\d{4})\b",
)

MONEY_PATTERN = (
    r"[0-9]{1,3}(?:[.,][0-9]{3})+(?:[.,][0-9]{1,2})?"
    r"|[0-9]+(?:[.,][0-9]{1,2})?"
)


class EmailParseError(ValueError):
    pass


def body_hash(raw_text: str) -> str:
    return hashlib.sha256(raw_text.strip().encode("utf-8")).hexdigest()


def parse_email_text(raw_text: str, received_at: datetime | None = None) -> ParsedEmailCandidate:
    text = raw_text.strip()
    if not text:
        raise EmailParseError("Email text is empty")

    normalized = _normalize(text)
    subject = _extract_header(text, ("subject", "asunto")) or _fallback_subject(text)
    sender = _extract_header(text, ("from", "de", "remitente"))
    sender_name, sender_email = _parse_sender(sender)
    money = _extract_money(text, normalized)
    merchant = _extract_merchant(normalized, text)
    counterparty = _extract_counterparty(text, normalized, merchant)
    suggested_type = _suggest_transaction_type(normalized)
    cashflow_direction = cashflow_direction_for_type(suggested_type)
    category_name, reason, confidence = _suggest_category(normalized, merchant, suggested_type)
    account_detection = _detect_account(normalized)
    splits = _suggest_splits(text, money.amount)
    needs_split = _needs_manual_split(merchant, normalized, splits)
    status = "needs_review" if needs_split or category_name == "Por revisar" else "classified"
    if money.currency != "CLP" and money.amount_clp is None:
        status = "needs_review"

    if needs_split:
        reason = "Supermercado sin detalle suficiente; revisar antes de guardar"

    return ParsedEmailCandidate(
        subject=subject[:240],
        body_preview=_preview(text),
        body_text=text,
        body_hash=body_hash(text),
        received_at=received_at or datetime.now(timezone.utc),
        sender_name=sender_name,
        sender_email=sender_email,
        amount=money.amount,
        currency=money.currency,
        original_amount=money.original_amount,
        original_currency=money.original_currency,
        amount_clp=money.amount_clp,
        exchange_rate=money.exchange_rate,
        exchange_rate_source=money.exchange_rate_source,
        exchange_rate_date=money.exchange_rate_date,
        currency_detection_confidence=money.confidence,
        currency_detection_reason=money.reason,
        merchant_name=merchant,
        counterparty=counterparty,
        description=subject,
        suggested_category_name=category_name,
        suggested_transaction_type=suggested_type,
        cashflow_direction=cashflow_direction,
        status=status,
        confidence=confidence,
        classification_reason=reason,
        needs_split=needs_split,
        detected_account_institution=account_detection["institution"],
        detected_account_type=account_detection["account_type"],
        detected_account_last_four=account_detection["last_four"],
        account_detection_confidence=account_detection["confidence"],
        account_detection_reason=account_detection["reason"],
        suggested_splits=splits,
    )


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(char for char in decomposed if not unicodedata.combining(char))
    return ascii_value.lower()


def _extract_header(text: str, names: tuple[str, ...]) -> str | None:
    for line in text.splitlines():
        normalized_line = _normalize(line)
        for name in names:
            if normalized_line.startswith(f"{name}:"):
                return line.split(":", 1)[1].strip()
    return None


def _fallback_subject(text: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned[:240]
    return "Correo importado"


def _parse_sender(sender: str | None) -> tuple[str | None, str | None]:
    if not sender:
        return None, None
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", sender)
    email = email_match.group(0) if email_match else None
    name = sender.replace(email or "", "").replace("<", "").replace(">", "").strip() or None
    return name, email


def _extract_money(text: str, normalized_text: str) -> DetectedMoney:
    explicit_usd = _extract_explicit_usd(text, normalized_text)
    if explicit_usd is not None:
        amount_clp = _extract_clp_equivalent(normalized_text)
        exchange_rate = (amount_clp / explicit_usd).quantize(Decimal("0.000001")) if amount_clp else None
        return DetectedMoney(
            amount=explicit_usd,
            currency="USD",
            original_amount=explicit_usd,
            original_currency="USD",
            amount_clp=amount_clp,
            exchange_rate=exchange_rate,
            exchange_rate_source="email" if exchange_rate else None,
            exchange_rate_date=None,
            confidence=0.94 if amount_clp else 0.88,
            reason="Monto USD detectado por indicador explicito US$/USD/dolares",
        )

    ambiguous_usd = _extract_ambiguous_usd(text, normalized_text)
    if ambiguous_usd is not None:
        return DetectedMoney(
            amount=ambiguous_usd,
            currency="USD",
            original_amount=ambiguous_usd,
            original_currency="USD",
            amount_clp=None,
            exchange_rate=None,
            exchange_rate_source=None,
            exchange_rate_date=None,
            confidence=0.56,
            reason="Monto decimal con comercio internacional; revisar moneda y equivalente CLP",
        )

    amount = _extract_amount_clp(text, normalized_text)
    return DetectedMoney(
        amount=amount,
        currency="CLP",
        original_amount=amount,
        original_currency="CLP",
        amount_clp=amount,
        exchange_rate=None,
        exchange_rate_source=None,
        exchange_rate_date=None,
        confidence=0.96,
        reason="Monto CLP detectado por simbolo $, pesos o formato bancario local",
    )


def _extract_explicit_usd(text: str, normalized_text: str) -> Decimal | None:
    patterns = [
        rf"(?:us\$|u\$s|usd)\s*({MONEY_PATTERN})",
        rf"({MONEY_PATTERN})\s*(?:usd|us\$|u\$s)",
        rf"(?:dolares?|dolares?\s+americanos?)\s*({MONEY_PATTERN})",
        rf"({MONEY_PATTERN})\s*(?:dolares?|dolares?\s+americanos?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if match:
            return _to_decimal(match.group(1), "USD")
    return None


def _extract_ambiguous_usd(text: str, normalized_text: str) -> Decimal | None:
    international_signal = any(
        signal in normalized_text
        for signal in (
            "openai",
            "chatgpt",
            "apple.com/bill",
            "google *",
            "amazon.com",
            "paypal",
            "steam",
            "netflix.com",
            "spotify usa",
            "cargo internacional",
            "compra internacional",
        )
    ) or re.search(r"\b(?:us|usa|eeuu|estados unidos)\b", normalized_text) is not None
    if not international_signal:
        return None

    patterns = [
        rf"(?:valor|monto|total|importe|cargo)\s*:?\s*({MONEY_PATTERN})",
        rf"(?:por)\s+({MONEY_PATTERN})",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if not match:
            continue
        raw_amount = match.group(1)
        if "." not in raw_amount and "," not in raw_amount:
            continue
        return _to_decimal(raw_amount, "USD")
    return None


def _extract_clp_equivalent(normalized_text: str) -> Decimal | None:
    patterns = [
        rf"(?:equivalente|monto\s+clp|cargo\s+en\s+pesos|valor\s+en\s+pesos|pesos\s+chilenos).{{0,80}}?\$?\s*({MONEY_PATTERN})\s*(?:clp|pesos)?",
        rf"(?:clp|pesos)\s*\$?\s*({MONEY_PATTERN})",
        rf"\$\s*({MONEY_PATTERN})\s*(?:clp|pesos)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if match:
            return _to_decimal(match.group(1), "CLP")
    return None


def _extract_amount_clp(text: str, normalized_text: str) -> Decimal:
    patterns = [
        rf"(?<!us)\$\s*({MONEY_PATTERN})",
        rf"(?:monto|total|valor|importe)"
        rf"(?:[ \t]+(?:recibido|pagado|cargado|abonado|de[ \t]+(?:la[ \t]+)?"
        rf"(?:compra|transaccion|operacion|transferencia)))?[ \t]*:?[ \t]*\$?[ \t]*({MONEY_PATTERN})",
        rf"(?:compra|abono|pago|cargo)"
        rf"(?:[ \t]+(?:por|de|recibido|realizado|efectuado|aprobado))?[ \t]*:?[ \t]*\$?[ \t]*({MONEY_PATTERN})",
        rf"(?:por\s+un\s+monto\s+de|por)\s*\$?\s*({MONEY_PATTERN})",
        rf"({MONEY_PATTERN})\s*(?:clp|pesos)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if match:
            return _to_decimal(match.group(1), "CLP")
    raise EmailParseError("Could not detect an amount")


def _to_decimal(value: str, currency: str) -> Decimal:
    cleaned = value.strip().replace(" ", "")
    if "." in cleaned and "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        parts = cleaned.split(",")
        cleaned = "".join(parts) if len(parts[-1]) == 3 else ".".join(parts)
    elif cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "")
    elif "." in cleaned and len(cleaned.rsplit(".", 1)[-1]) == 3:
        cleaned = cleaned.replace(".", "")

    try:
        quantizer = Decimal("1") if currency == "CLP" else Decimal("0.01")
        return Decimal(cleaned).quantize(quantizer)
    except InvalidOperation as exc:
        raise EmailParseError("Invalid amount format") from exc


def _extract_merchant(normalized: str, original: str) -> str | None:
    explicit = re.search(r"(?:^|\n)\s*(?:comercio|merchant|tienda|establecimiento|local)\s*:\s*([^\n\r]+)", original, flags=re.IGNORECASE)
    if explicit:
        return explicit.group(1).strip()[:160]
    purchase_location = re.search(
        r"(?:compra|cargo).{0,220}?\s+en\s+(.+?)\s+(?:el\s+\d{1,2}/\d{1,2}/\d{4}|con\s+fecha|fecha\s+|$)",
        original,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if purchase_location:
        merchant = " ".join(purchase_location.group(1).split()).strip(" .,:;-")
        if merchant:
            return merchant[:160]
    for keyword, merchant in MERCHANT_KEYWORDS.items():
        if keyword in normalized:
            return merchant
    return None


def _extract_counterparty(original: str, normalized: str, merchant: str | None) -> str | None:
    received_transfer = re.search(
        r"(?:has\s+recibido|recibiste).{0,80}?transferencia(?:\s+de\s+fondos)?\s+de\s+(.+?)\s+hacia\s+tu\s+cuenta",
        original,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if received_transfer:
        counterparty = " ".join(received_transfer.group(1).split()).strip(" .,:;-")
        if counterparty:
            return counterparty[:160]
    explicit = re.search(r"(?:^|\n)\s*(?:de|desde|origen|remitente)\s*:\s*([^\n\r<]+)", original, flags=re.IGNORECASE)
    if explicit and any(word in normalized for word in ("transferencia", "abono", "recibiste", "recibida", "has recibido", "recibido")):
        return explicit.group(1).strip()[:160]
    if merchant is None and any(word in normalized for word in ("transferencia", "abono", "recibiste", "recibida", "has recibido", "recibido")):
        sender = _extract_header(original, ("from", "de", "remitente"))
        sender_name, _ = _parse_sender(sender)
        return sender_name
    return None


def _is_internal_transfer(normalized: str) -> bool:
    return any(
        phrase in normalized
        for phrase in (
            "entre tus cuentas",
            "entre mis cuentas",
            "entre cuentas propias",
            "entre cuentas propias del titular",
            "traspaso entre cuentas",
            "transferencia entre cuentas",
            "traspaso entre tus cuentas",
            "transferencia entre tus cuentas",
            "traspaso entre tus productos",
            "transferencia entre tus productos",
            "traspaso a tu cuenta",
            "traspaso a cuenta propia",
            "transferencia a cuenta propia",
            "transferencia a tu cuenta de ahorro",
            "abono entre cuentas",
        )
    )


def _suggest_transaction_type(normalized: str) -> str:
    if any(word in normalized for word in ("aporte inversion", "inverti", "compra de fondos", "compra fondo", "deposito inversion")):
        return "investment"
    if any(word in normalized for word in ("rescate inversion", "retiro inversion", "rescate de fondos", "venta de fondos")):
        return "disinvestment"
    if any(word in normalized for word in ("devolucion", "reembolso")):
        return "refund"
    if any(word in normalized for word in ("suscripcion", "spotify", "netflix", "youtube", "icloud")):
        return "subscription"
    if _is_internal_transfer(normalized):
        return "internal_transfer"
    incoming_signal = any(
        word in normalized
        for word in (
            "transferencia recibida",
            "transferencia desde",
            "has recibido una transferencia",
            "has recibido transferencia",
            "transferencia de fondos de",
            "monto recibido",
            "recibiste",
            "abono recibido",
            "abono en cuenta",
            "abono a tu cuenta",
            "se ha abonado",
            "se abono",
            "se acredito",
            "deposito recibido",
            "pago recibido",
            "te transfirio",
            "sueldo",
            "honorarios",
        )
    )
    if incoming_signal and any(word in normalized for word in ("clase", "ayudantia", "tutoria", "alumno")):
        return "income"
    if incoming_signal:
        return "transfer_in"
    if any(
        word in normalized
        for word in (
            "compra aprobada",
            "compra realizada",
            "compra por",
            "se ha realizado una compra",
            "se realizo una compra",
            "cargo aprobado",
            "cargo en tarjeta",
            "cargo en cuenta",
            "debito en cuenta",
            "pago realizado",
            "pago efectuado",
            "transferencia enviada",
            "transferencia a terceros",
            "comprobante de transferencia a terceros",
            "enviaste",
            "transferiste",
            "has realizado una transferencia",
            "giro en cajero",
            "retiro en cajero",
        )
    ):
        if "transferencia" in normalized or "enviaste" in normalized or "transferiste" in normalized:
            return "transfer_out"
        return "expense"
    return "expense"


def cashflow_direction_for_type(transaction_type: str) -> str:
    if transaction_type in {"income", "transfer_in", "receivable_payment", "refund", "disinvestment"}:
        return "inflow"
    if transaction_type in {"expense", "subscription", "transfer_out", "payable_payment", "loan_out", "investment"}:
        return "outflow"
    return "neutral"


def _detect_account(normalized: str) -> dict[str, str | float | None]:
    institution = _detect_institution(normalized)
    account_type = _detect_account_type(normalized)
    last_four = _detect_last_four(normalized)

    signals = [bool(institution), bool(account_type), bool(last_four)]
    if not any(signals):
        return {"institution": None, "account_type": None, "last_four": None, "confidence": None, "reason": None}

    confidence = 0.1 + (0.3 if institution else 0) + (0.3 if account_type else 0) + (0.35 if last_four else 0)
    reason_parts = []
    if institution:
        reason_parts.append(f"institucion {institution}")
    if account_type:
        reason_parts.append(f"tipo {account_type}")
    if last_four:
        reason_parts.append(f"ultimos digitos {last_four}")
    return {
        "institution": institution,
        "account_type": account_type,
        "last_four": last_four,
        "confidence": min(confidence, 0.95),
        "reason": ", ".join(reason_parts),
    }


def _detect_institution(normalized: str) -> str | None:
    padded = f" {normalized} "
    for aliases, label in INSTITUTION_ALIASES:
        if any(alias in padded for alias in aliases):
            return label
    return None


def _detect_account_type(normalized: str) -> str | None:
    if any(word in normalized for word in ("tarjeta de debito", "tarjeta debito", "redcompra", "debito")):
        account_type = "debit_card"
    elif any(word in normalized for word in ("tarjeta de credito", "tarjeta credito", "tarj. credito", "t. credito")):
        account_type = "credit_card"
    elif re.search(r"\b(?:visa|mastercard|amex)\b", normalized) and "debito" not in normalized:
        account_type = "credit_card"
    elif "cuenta corriente" in normalized or "cta corriente" in normalized or "cta. corriente" in normalized:
        account_type = "checking"
    elif "cuenta vista" in normalized or "cuenta de ahorro" in normalized:
        account_type = "savings"
    elif "wallet" in normalized or "billetera" in normalized:
        account_type = "wallet"
    else:
        account_type = None
    return account_type


def _detect_last_four(normalized: str) -> str | None:
    for pattern in LAST_FOUR_PATTERNS:
        match = re.search(pattern, normalized)
        if match:
            return match.group(1)
    return None


def _suggest_category(normalized: str, merchant: str | None, transaction_type: str) -> tuple[str, str, float]:
    if transaction_type == "investment":
        return "Inversiones", "Aporte o compra de inversion detectada", 0.78
    if transaction_type == "disinvestment":
        return "Desinversiones", "Rescate o retiro de inversion detectado", 0.78
    if transaction_type in {"income", "transfer_in"} and any(word in normalized for word in ("clase", "ayudantia", "tutoria", "alumno")):
        return "Clases", "Transferencia asociada a clases o ayudantias", 0.86
    if transaction_type == "receivable_payment":
        return "Cuentas por cobrar", "Pago asociado a cuenta por cobrar", 0.72
    if merchant in SUPERMARKETS:
        return "Supermercado", "Comercio reconocido como supermercado", 0.8
    if merchant in SUBSCRIPTIONS:
        return "Suscripciones", "Comercio reconocido como suscripcion", 0.84
    if merchant in DELIVERY or any(word in normalized for word in ("restaurant", "almuerzo", "comida", "delivery")):
        return "Comida", "Delivery o comida detectada por palabra clave", 0.76
    if merchant in ONLINE_SHOPS:
        return "Compras online", "Comercio online reconocido", 0.76
    if any(word in normalized for word in ("uber", "cabify", "metro", "bip", "transporte")):
        return "Transporte", "Transporte detectado por palabra clave", 0.74
    if transaction_type == "internal_transfer":
        return "Transferencias", "Traspaso entre cuentas propias detectado", 0.7
    if transaction_type in {"transfer_in", "transfer_out"}:
        return "Transferencias", "Transferencia sin categoria mas especifica", 0.64
    if transaction_type == "income":
        return "Ingresos", "Ingreso sin categoria mas especifica", 0.64
    return "Por revisar", "Sin regla suficiente para clasificar", 0.35


def _suggest_splits(text: str, amount: Decimal) -> list[ParsedSplit]:
    normalized = _normalize(text)
    category_scores = {
        "Comida": sum(1 for word in FOOD_WORDS if word in normalized),
        "Golosinas": sum(1 for word in SNACK_WORDS if word in normalized),
        "Aseo y limpieza": sum(1 for word in CLEANING_WORDS if word in normalized),
    }
    present = [category for category, score in category_scores.items() if score > 0]
    if len(present) < 2:
        return []

    base = (amount / Decimal(len(present))).quantize(Decimal("1"))
    splits: list[ParsedSplit] = []
    allocated = Decimal("0")
    for index, category in enumerate(present):
        split_amount = amount - allocated if index == len(present) - 1 else base
        allocated += split_amount
        splits.append(ParsedSplit(category_name=category, amount=split_amount, label=f"Sugerido {category}"))
    return splits


def _needs_manual_split(merchant: str | None, normalized: str, splits: list[ParsedSplit]) -> bool:
    if merchant not in SUPERMARKETS:
        return False
    if splits:
        return False
    detail_words = FOOD_WORDS | SNACK_WORDS | CLEANING_WORDS
    return not any(word in normalized for word in detail_words)


def _preview(text: str) -> str:
    collapsed = " ".join(text.split())
    return collapsed[:500]
