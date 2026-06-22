from decimal import Decimal, InvalidOperation


SUPPORTED_CURRENCIES = {"CLP", "USD"}


def normalize_currency(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.upper()
    if normalized not in SUPPORTED_CURRENCIES:
        raise ValueError("Currency must be CLP or USD")
    return normalized


def validate_money_scale(value: Decimal | None, currency: str | None, field_name: str = "amount") -> None:
    if value is None or currency is None:
        return
    try:
        if currency == "CLP" and value != value.quantize(Decimal("1")):
            raise ValueError(f"{field_name} in CLP must not include decimals")
        if currency == "USD" and value != value.quantize(Decimal("0.01")):
            raise ValueError(f"{field_name} in USD can include at most two decimals")
    except InvalidOperation as exc:
        raise ValueError(f"{field_name} has an invalid money format") from exc


def quantize_money(value: Decimal, currency: str) -> Decimal:
    return value.quantize(Decimal("1") if currency == "CLP" else Decimal("0.01"))
