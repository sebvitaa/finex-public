from alembic import command
from alembic.config import Config
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import PROJECT_ROOT
from backend.app.db.session import SessionLocal
from backend.app.models import Category, ClassificationRule, FinancialAccount


BASE_CATEGORIES = [
    {"name": "Comida", "color": "#22C55E", "icon": "utensils", "kind": "expense", "sort_order": 10},
    {"name": "Golosinas", "color": "#F472B6", "icon": "candy", "kind": "expense", "sort_order": 15},
    {"name": "Transporte", "color": "#38BDF8", "icon": "car", "kind": "expense", "sort_order": 20},
    {"name": "Supermercado", "color": "#A78BFA", "icon": "shopping-basket", "kind": "expense", "sort_order": 30},
    {"name": "Aseo y limpieza", "color": "#2DD4BF", "icon": "spray-can", "kind": "expense", "sort_order": 35},
    {"name": "Ocio", "color": "#F59E0B", "icon": "ticket", "kind": "expense", "sort_order": 40},
    {"name": "Salud", "color": "#EF4444", "icon": "heart-pulse", "kind": "expense", "sort_order": 50},
    {"name": "Educacion", "color": "#60A5FA", "icon": "graduation-cap", "kind": "expense", "sort_order": 60},
    {"name": "Servicios", "color": "#F97316", "icon": "receipt", "kind": "expense", "sort_order": 70},
    {"name": "Suscripciones", "color": "#EC4899", "icon": "repeat", "kind": "expense", "sort_order": 80},
    {"name": "Transferencias", "color": "#14B8A6", "icon": "send", "kind": "both", "sort_order": 90},
    {"name": "Compras online", "color": "#8B5CF6", "icon": "package", "kind": "expense", "sort_order": 100},
    {"name": "Hogar", "color": "#84CC16", "icon": "home", "kind": "expense", "sort_order": 110},
    {"name": "Ingresos", "color": "#22C55E", "icon": "arrow-down-circle", "kind": "income", "sort_order": 115},
    {"name": "Clases", "color": "#60A5FA", "icon": "book-open", "kind": "income", "sort_order": 116},
    {"name": "Cuentas por cobrar", "color": "#F59E0B", "icon": "hand-coins", "kind": "both", "sort_order": 117},
    {"name": "Cuentas por pagar", "color": "#FB7185", "icon": "receipt-text", "kind": "both", "sort_order": 118},
    {"name": "Ingreso por ajuste", "color": "#4ADE80", "icon": "badge-dollar-sign", "kind": "income", "sort_order": 119},
    {"name": "Costo por ajuste", "color": "#FB7185", "icon": "badge-minus", "kind": "expense", "sort_order": 120},
    {"name": "Inversiones", "color": "#38BDF8", "icon": "trending-up", "kind": "both", "sort_order": 121},
    {"name": "Desinversiones", "color": "#A78BFA", "icon": "trending-down", "kind": "both", "sort_order": 122},
    {"name": "Otros", "color": "#71717A", "icon": "circle-ellipsis", "kind": "both", "sort_order": 130},
    {"name": "Por revisar", "color": "#F59E0B", "icon": "alert-circle", "kind": "both", "sort_order": 140},
]


BASE_RULES = [
    {"name": "Spotify a suscripciones", "pattern": "spotify", "category": "Suscripciones", "transaction_type": "subscription", "priority": 10, "confidence": 0.9},
    {"name": "Netflix a suscripciones", "pattern": "netflix", "category": "Suscripciones", "transaction_type": "subscription", "priority": 11, "confidence": 0.88},
    {"name": "YouTube a suscripciones", "pattern": "youtube", "category": "Suscripciones", "transaction_type": "subscription", "priority": 12, "confidence": 0.86},
    {"name": "iCloud a suscripciones", "pattern": "icloud", "category": "Suscripciones", "transaction_type": "subscription", "priority": 13, "confidence": 0.86},
    {"name": "Uber a transporte", "pattern": "uber", "category": "Transporte", "transaction_type": "expense", "priority": 20, "confidence": 0.86},
    {"name": "Cabify a transporte", "pattern": "cabify", "category": "Transporte", "transaction_type": "expense", "priority": 21, "confidence": 0.84},
    {"name": "Metro/Bip a transporte", "pattern": "bip", "category": "Transporte", "transaction_type": "expense", "priority": 22, "confidence": 0.78},
    {"name": "Rappi a comida", "pattern": "rappi", "category": "Comida", "transaction_type": "expense", "priority": 30, "confidence": 0.8},
    {"name": "PedidosYa a comida", "pattern": "pedidosya", "category": "Comida", "transaction_type": "expense", "priority": 31, "confidence": 0.8},
    {"name": "Lider a supermercado", "pattern": "lider", "category": "Supermercado", "transaction_type": "expense", "priority": 40, "confidence": 0.86},
    {"name": "Jumbo a supermercado", "pattern": "jumbo", "category": "Supermercado", "transaction_type": "expense", "priority": 41, "confidence": 0.86},
    {"name": "Unimarc a supermercado", "pattern": "unimarc", "category": "Supermercado", "transaction_type": "expense", "priority": 42, "confidence": 0.86},
    {"name": "Tottus a supermercado", "pattern": "tottus", "category": "Supermercado", "transaction_type": "expense", "priority": 43, "confidence": 0.86},
    {"name": "Golosinas por texto", "pattern": "chocolate", "category": "Golosinas", "transaction_type": "expense", "priority": 50, "confidence": 0.72},
    {"name": "Comida por texto", "pattern": "almuerzo", "category": "Comida", "transaction_type": "expense", "priority": 55, "confidence": 0.72},
    {"name": "Aseo por texto", "pattern": "detergente", "category": "Aseo y limpieza", "transaction_type": "expense", "priority": 60, "confidence": 0.72},
    {"name": "Clases recibidas", "pattern": "clase", "category": "Clases", "transaction_type": "income", "priority": 70, "confidence": 0.86},
    {"name": "Ayudantias recibidas", "pattern": "ayudantia", "category": "Clases", "transaction_type": "income", "priority": 71, "confidence": 0.86},
    {"name": "Pago cuenta por cobrar", "pattern": "cuenta por cobrar", "category": "Cuentas por cobrar", "transaction_type": "receivable_payment", "priority": 75, "confidence": 0.78},
    {"name": "Pago cuenta por pagar", "pattern": "cuenta por pagar", "category": "Cuentas por pagar", "transaction_type": "payable_payment", "priority": 76, "confidence": 0.78},
    {"name": "Mercado Pago online", "pattern": "mercado pago", "category": "Compras online", "transaction_type": "expense", "priority": 80, "confidence": 0.76},
    {"name": "Mercado Libre online", "pattern": "mercadolibre", "category": "Compras online", "transaction_type": "expense", "priority": 81, "confidence": 0.76},
    {"name": "Amazon online", "pattern": "amazon", "category": "Compras online", "transaction_type": "expense", "priority": 82, "confidence": 0.76},
    {"name": "Transferencia recibida", "pattern": "transferencia recibida", "category": "Transferencias", "transaction_type": "transfer_in", "priority": 90, "confidence": 0.8},
    {"name": "Transferencia a terceros", "pattern": "transferencia a terceros", "category": "Transferencias", "transaction_type": "transfer_out", "priority": 91, "confidence": 0.8},
    {"name": "Banco Edwards compra tarjeta", "field": "sender_email", "pattern": "bancoedwards.cl", "category": "Por revisar", "transaction_type": "expense", "priority": 95, "confidence": 0.62},
    {"name": "Banco de Chile transferencias", "field": "sender_email", "pattern": "bancochile.cl", "category": "Transferencias", "transaction_type": "transfer_out", "priority": 96, "confidence": 0.62},
    {"name": "Aporte inversion", "pattern": "aporte inversion", "category": "Inversiones", "transaction_type": "investment", "priority": 100, "confidence": 0.82},
    {"name": "Compra fondos", "pattern": "compra de fondos", "category": "Inversiones", "transaction_type": "investment", "priority": 101, "confidence": 0.82},
    {"name": "Rescate inversion", "pattern": "rescate inversion", "category": "Desinversiones", "transaction_type": "disinvestment", "priority": 102, "confidence": 0.82},
    {"name": "Retiro inversion", "pattern": "retiro inversion", "category": "Desinversiones", "transaction_type": "disinvestment", "priority": 103, "confidence": 0.82},
]


BASE_FINANCIAL_ACCOUNTS = [
    {
        "name": "Credito CLP · 7459",
        "institution": "Banco Edwards",
        "account_type": "credit_card",
        "product_name": "Tarjeta de credito",
        "last_four": "7459",
        "currency": "CLP",
        "opening_balance": Decimal("0.00"),
        "credit_limit_amount": Decimal("1000000.00"),
        "credit_limit_currency": "CLP",
        "billing_cycle_day": 1,
        "payment_due_day": 10,
        "statement_currency": "CLP",
        "card_art_variant": "black",
        "visual_group": "Credito 7459",
    },
    {
        "name": "Credito USD · 7459",
        "institution": "Banco Edwards",
        "account_type": "credit_card",
        "product_name": "Tarjeta de credito",
        "last_four": "7459",
        "currency": "USD",
        "opening_balance": Decimal("0.00"),
        "credit_limit_amount": Decimal("1000.00"),
        "credit_limit_currency": "USD",
        "billing_cycle_day": 1,
        "payment_due_day": 10,
        "statement_currency": "USD",
        "card_art_variant": "blue",
        "visual_group": "Credito 7459",
    },
]


def seed_categories(session: Session) -> None:
    existing_names = set(session.scalars(select(Category.name)).all())

    for category_data in BASE_CATEGORIES:
        if category_data["name"] in existing_names:
            continue
        session.add(Category(**category_data, is_system=True))

    session.commit()


def seed_financial_accounts(session: Session) -> None:
    existing = {
        (account.last_four, account.account_type, account.currency)
        for account in session.scalars(select(FinancialAccount)).all()
    }
    for account_data in BASE_FINANCIAL_ACCOUNTS:
        key = (account_data["last_four"], account_data["account_type"], account_data["currency"])
        if key in existing:
            continue
        session.add(FinancialAccount(**account_data))
    session.commit()


def seed_classification_rules(session: Session) -> None:
    categories = {category.name: category for category in session.scalars(select(Category)).all()}
    existing = {
        (rule.name, rule.field, rule.operator, rule.pattern)
        for rule in session.scalars(select(ClassificationRule)).all()
    }
    for rule_data in BASE_RULES:
        field = rule_data.get("field", "source_text")
        operator = rule_data.get("operator", "contains")
        key = (rule_data["name"], field, operator, rule_data["pattern"])
        if key in existing:
            continue
        category = categories.get(rule_data["category"])
        if category is None:
            continue
        session.add(
            ClassificationRule(
                name=rule_data["name"],
                field=field,
                operator=operator,
                pattern=rule_data["pattern"],
                category_id=category.id,
                transaction_type=rule_data.get("transaction_type"),
                priority=rule_data["priority"],
                confidence=rule_data["confidence"],
                is_active=True,
                created_from_correction=False,
            )
        )
    session.commit()


def run_migrations(session_name: str = "personal") -> None:
    from backend.app.db.session import db_url_for

    alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(PROJECT_ROOT / "backend/alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url_for(session_name))
    command.upgrade(alembic_cfg, "head")


def init_db(session_name: str = "personal") -> None:
    from backend.app.db.session import get_session

    run_migrations(session_name)
    with next(get_session(session_name)) as session:
        seed_categories(session)
        seed_classification_rules(session)
        seed_financial_accounts(session)


def init_demo_db(seed: int | None = None) -> None:
    """Seed the demo DB. ``seed=None`` → date-derived data (consistent each day);
    an explicit seed → fresh random data (used by the "Reiniciar datos" reset)."""
    from backend.app.db.seed_demo import seed_demo_data
    from backend.app.db.session import get_session

    init_db("demo")
    with next(get_session("demo")) as session:
        seed_demo_data(session, seed=seed)
