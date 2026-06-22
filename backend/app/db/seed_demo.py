"""Demo data seeder — fully invented, anonymized data for presentation mode.

Everything here is fictional. The goal is a rich, six-month dataset (income from
classes per student, recurring subscriptions and services, varied daily expenses,
transfers in/out between people, investments and obligations) so every dashboard
insight has real material to work with.

Two behaviours, controlled by the RNG seed passed to ``seed_demo_data``:

* No seed (default) → the seed is derived from the *current date*, so the dataset
  looks identical throughout the day and shifts naturally from one day to the
  next ("consistent each day").
* Explicit seed → the "Reiniciar datos demo" button passes a fresh random seed so
  every reset reshuffles into brand-new random data.

The date anchors are also computed from the real "today": prior months are fully
populated and the current month fills up day by day, up to today.

NOTE: this only ever touches the *demo* database. The personal/real data is never
generated or modified here.
"""

import random
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import (
    Category,
    FinancialAccount,
    InvestmentAccount,
    InvestmentMovement,
    Payable,
    Person,
    Receivable,
    Transaction,
    TransactionSplit,
)

# Date anchors are computed dynamically inside ``seed_demo_data`` from the real
# "today" (see module docstring), so there are no hardcoded period constants here.


def _utc(year: int, month: int, day: int, hour: int = 12, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _cat(session: Session, name: str) -> int | None:
    return session.scalar(select(Category.id).where(Category.name == name))


def seed_demo_data(session: Session, *, seed: int | None = None) -> None:
    # ------------------------------------------------------------------
    # Guard: skip if demo data already exists
    # ------------------------------------------------------------------
    if session.scalar(select(Person.id)) is not None:
        return

    # ------------------------------------------------------------------
    # Date anchors — derived from the real "today" so the demo always shows the
    # current month filling up day by day, with the prior months fully populated.
    # ------------------------------------------------------------------
    now = datetime.now(timezone.utc)
    demo_year = now.year
    current_month = now.month
    current_day_limit = now.day  # the current month is partial, up to today
    start_month = max(1, current_month - 5)
    months = list(range(start_month, current_month + 1))

    # Seed selection (see module docstring): no seed → date-derived (consistent
    # each day); explicit seed → fresh random data on every "Reiniciar datos".
    if seed is None:
        seed = demo_year * 10_000 + current_month * 100 + current_day_limit

    def _rel(months_back: int, day: int, hour: int = 12) -> datetime:
        """A date `months_back` months before the current one (day clamped to 28)."""
        m = current_month - months_back
        y = demo_year
        while m < 1:
            m += 12
            y -= 1
        return _utc(y, m, min(day, 28), hour)

    # Hide the base-seeded accounts (e.g. Banco Edwards) so the demo only shows
    # its own fully-invented accounts.
    for base_account in session.scalars(select(FinancialAccount)).all():
        base_account.is_active = False
    session.flush()

    rng = random.Random(seed)

    # ------------------------------------------------------------------
    # People (students + contacts)
    # ------------------------------------------------------------------
    andres = Person(name="Andrés Muñoz", alias="Andrés", email="andres.munoz@example.com")
    valentina = Person(name="Valentina Torres", alias="Vale", email="vtorres@example.com")
    sofia = Person(name="Sofía Reyes", alias="Sofi", phone="+56 9 1234 5678")
    camila = Person(name="Camila Rojas", alias="Cami", email="cami.rojas@example.com")
    diego = Person(name="Diego Soto", alias="Diego", phone="+56 9 8765 4321")
    session.add_all([andres, valentina, sofia, camila, diego])
    session.flush()

    # Students who pay monthly classes (name, person, monthly fee)
    students = [
        (andres, 160_000),
        (valentina, 150_000),
        (sofia, 140_000),
        (camila, 120_000),
    ]

    # ------------------------------------------------------------------
    # Financial accounts
    # ------------------------------------------------------------------
    cc_bci = FinancialAccount(
        name="Cuenta Corriente BCI · 4821",
        institution="BCI",
        account_type="checking",
        product_name="Cuenta Corriente",
        last_four="4821",
        currency="CLP",
        opening_balance=Decimal("850000.00"),
        card_art_variant="blue",
        visual_group="BCI",
    )
    tc_falabella = FinancialAccount(
        name="Tarjeta Crédito Falabella · 3316",
        institution="Falabella",
        account_type="credit_card",
        product_name="CMR Falabella",
        last_four="3316",
        currency="CLP",
        opening_balance=Decimal("0.00"),
        credit_limit_amount=Decimal("800000.00"),
        credit_limit_currency="CLP",
        billing_cycle_day=5,
        payment_due_day=20,
        statement_currency="CLP",
        card_art_variant="green",
        visual_group="Falabella",
    )
    vista_tenpo = FinancialAccount(
        name="Cuenta Vista Tenpo · 9043",
        institution="Tenpo",
        account_type="wallet",
        product_name="Cuenta Vista",
        last_four="9043",
        currency="CLP",
        opening_balance=Decimal("120000.00"),
        card_art_variant="black",
        visual_group="Tenpo",
    )
    session.add_all([cc_bci, tc_falabella, vista_tenpo])
    session.flush()

    bci_id = cc_bci.id
    fala_id = tc_falabella.id
    tenpo_id = vista_tenpo.id

    # ------------------------------------------------------------------
    # Investment accounts
    # ------------------------------------------------------------------
    inv_fmi = InvestmentAccount(
        name="FMI Conservador",
        institution="BCI Asset Management",
        account_type="mutual_fund",
        currency="CLP",
        current_value=Decimal("742000.00"),
    )
    inv_fintual = InvestmentAccount(
        name="Risky Norris",
        institution="Fintual",
        account_type="brokerage",
        currency="CLP",
        current_value=Decimal("388500.00"),
    )
    session.add_all([inv_fmi, inv_fintual])
    session.flush()
    inv_fmi_id = inv_fmi.id
    inv_fintual_id = inv_fintual.id

    # ------------------------------------------------------------------
    # Receivables / Payables (obligations by person)
    # ------------------------------------------------------------------
    session.add_all([
        Receivable(
            person_id=andres.id, title="Almuerzo en el campus",
            original_amount=Decimal("18000.00"), remaining_amount=Decimal("18000.00"),
            currency="CLP", issued_at=_rel(2, 22), status="pending_payment",
            notes="Almorzamos en la cantina, quedó debiéndome",
        ),
        Receivable(
            person_id=valentina.id, title="Entradas concierto",
            original_amount=Decimal("42000.00"), remaining_amount=Decimal("21000.00"),
            currency="CLP", issued_at=_rel(1, 10), status="partially_paid",
        ),
        Receivable(
            person_id=camila.id, title="Préstamo fin de semana",
            original_amount=Decimal("30000.00"), remaining_amount=Decimal("30000.00"),
            currency="CLP", issued_at=_rel(1, 24), due_at=_rel(0, 15),
            status="pending_payment",
        ),
        Receivable(
            person_id=diego.id, title="Cena cumpleaños",
            original_amount=Decimal("25000.00"), remaining_amount=Decimal("25000.00"),
            currency="CLP", issued_at=_rel(2, 5), due_at=_rel(1, 5),
            status="pending_payment", notes="Le cubrí la cena, vencida",
        ),
    ])
    session.add_all([
        Payable(
            person_id=sofia.id, title="Parte arriendo marzo",
            original_amount=Decimal("65000.00"), remaining_amount=Decimal("65000.00"),
            currency="CLP", issued_at=_rel(3, 1), due_at=_rel(0, 30),
            status="pending_payment",
            notes="Me prestó para el arriendo mientras llegaba el depósito",
        ),
        Payable(
            person_id=diego.id, title="Me cubrió los Uber",
            original_amount=Decimal("12000.00"), remaining_amount=Decimal("12000.00"),
            currency="CLP", issued_at=_rel(1, 18), status="pending_payment",
        ),
    ])
    session.flush()

    # ------------------------------------------------------------------
    # Category lookup
    # ------------------------------------------------------------------
    cat = {
        name: _cat(session, name)
        for name in [
            "Comida", "Golosinas", "Transporte", "Supermercado", "Aseo y limpieza",
            "Ocio", "Salud", "Servicios", "Suscripciones", "Transferencias",
            "Compras online", "Hogar", "Ingresos", "Clases", "Inversiones",
            "Desinversiones", "Otros", "Por revisar",
        ]
    }

    # ------------------------------------------------------------------
    # Transaction helper
    # ------------------------------------------------------------------
    def tx(
        occurred_at: datetime,
        amount: int | Decimal,
        merchant_name: str,
        transaction_type: str,
        category_name: str,
        *,
        description: str | None = None,
        financial_account_id: int | None = None,
        investment_account_id: int | None = None,
        person_id: int | None = None,
        counterparty: str | None = None,
        status: str = "classified",
        source: str = "manual",
        relationship_category: str = "mi",
        confidence: float = 0.95,
        notes: str | None = None,
    ) -> Transaction:
        value = amount if isinstance(amount, Decimal) else Decimal(str(amount))
        return Transaction(
            occurred_at=occurred_at,
            amount=value,
            currency="CLP",
            original_currency="CLP",
            amount_clp=value,
            merchant_name=merchant_name,
            counterparty=counterparty,
            description=description,
            transaction_type=transaction_type,
            category_id=cat.get(category_name),
            financial_account_id=financial_account_id,
            investment_account_id=investment_account_id,
            person_id=person_id,
            status=status,
            source=source,
            relationship_category=relationship_category,
            confidence=confidence,
            classification_method="demo_seed",
            notes=notes,
        )

    # Merchant pools per category for varied, realistic-looking data
    POOLS = {
        "Supermercado": ["Jumbo Mall Plaza", "Lider Express", "Tottus Apoquindo", "Unimarc", "Jumbo Express", "Lider Hiper"],
        "Comida": ["Rappi", "PedidosYa", "Café Quínoa", "Sushi Club", "Pizza Hut", "Empanadas Don Rubén", "Sandwich Nico", "Café Dos Monos"],
        "Transporte": ["Uber", "Cabify", "Red Metropolitana (Bip!)", "Bip! recarga"],
        "Golosinas": ["Starbucks", "OK Market", "Almac corner", "Kiosco campus"],
        "Salud": ["Farmacia Cruz Verde", "Farmacia Ahumada", "Salcobrand"],
        "Ocio": ["Cineplanet", "Steam", "Teatro Caupolicán", "Lollapalooza tickets"],
        "Compras online": ["Mercado Libre", "AliExpress", "Amazon", "Paris.cl"],
    }

    SUBSCRIPTIONS = [
        ("Spotify", 6490), ("Netflix", 8990), ("iCloud 200 GB", 1290),
        ("YouTube Premium", 3490), ("Disney+", 5500),
    ]
    SERVICES = [
        ("Enel — luz", (17000, 21000)), ("Internet Movistar", (32000, 32000)),
        ("Aguas Andinas", (11000, 15000)), ("Gas Lipigas", (9000, 14000)),
    ]

    all_txs: list[Transaction] = []
    pending_splits: list[tuple[Transaction, list[tuple[str, int, str]]]] = []
    pending_moves: list[tuple[Transaction, str, int, datetime, str]] = []

    def in_month(month: int, day: int) -> bool:
        if month == current_month:
            return day <= current_day_limit
        return True

    def add(*txs: Transaction) -> None:
        all_txs.extend(t for t in txs if in_month(t.occurred_at.month, t.occurred_at.day))

    def pick_day(month: int, lo: int = 1, hi: int = 28) -> int:
        """A random day in [lo, hi], clamped so the current month never goes past today."""
        hi_eff = min(hi, current_day_limit) if month == current_month else hi
        return rng.randint(lo, max(lo, hi_eff))

    month_names = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
        7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
    }

    for month in months:
        name = month_names[month]

        # --- Income: monthly classes per student, spread across the whole month ---
        for student, fee in students:
            jitter = rng.choice([0, 0, 5000, -5000, 10000, 15000, -10000])
            add(tx(_utc(demo_year, month, pick_day(month, 1, 28), 9), fee + jitter, student.name, "income", "Clases",
                   description=f"Clases particulares {name}", financial_account_id=bci_id,
                   counterparty="Transferencia recibida", person_id=student.id))

        # --- Occasional extra income (ayudantías / clases de recuperación) ---
        for _ in range(rng.randint(0, 2)):
            add(tx(_utc(demo_year, month, pick_day(month, 1, 28), 10), rng.randrange(20000, 60000, 1000),
                   rng.choice(["Ayudantía universidad", "Clase de recuperación", "Taller fin de semana"]),
                   "income", "Clases", description=f"Ingreso extra {name}", financial_account_id=bci_id,
                   counterparty="Transferencia recibida"))

        # --- Recurring subscriptions (same amount monthly → detected as subscriptions) ---
        for sidx, (merchant, price) in enumerate(SUBSCRIPTIONS):
            # A fixed charge day per subscription, spread across the first half of the month.
            add(tx(_utc(demo_year, month, 2 + sidx * 3), price, merchant, "subscription", "Suscripciones",
                   financial_account_id=bci_id, confidence=0.92))

        # --- Services (utility bills spread across the month) ---
        for vidx, (merchant, (lo, hi)) in enumerate(SERVICES):
            amount = lo if lo == hi else rng.randrange(lo, hi, 100)
            add(tx(_utc(demo_year, month, 2 + vidx * 3), amount, merchant, "expense", "Servicios",
                   financial_account_id=bci_id))

        # --- Supermarket (2-3), one with a 3-way split ---
        n_super = rng.choice([2, 3, 3])
        for i in range(n_super):
            amount = rng.randrange(18000, 55000, 100)
            day = rng.randint(3, 26)
            merchant = rng.choice(POOLS["Supermercado"])
            t = tx(_utc(demo_year, month, day), amount, merchant, "expense", "Supermercado",
                   financial_account_id=fala_id)
            if in_month(month, day):
                all_txs.append(t)
                if i == 0:  # split the first supermarket purchase
                    food = int(amount * 0.55)
                    clean = int(amount * 0.25)
                    sweets = amount - food - clean
                    pending_splits.append((t, [
                        ("Supermercado", food, "Comida y abarrotes"),
                        ("Aseo y limpieza", clean, "Aseo y limpieza"),
                        ("Golosinas", sweets, "Snacks"),
                    ]))

        # --- Comida (5-7) ---
        for _ in range(rng.randint(5, 7)):
            amount = rng.randrange(6000, 18000, 100)
            day = rng.randint(2, 27)
            acct = rng.choice([fala_id, bci_id])
            add(tx(_utc(demo_year, month, day), amount, rng.choice(POOLS["Comida"]), "expense", "Comida",
                   financial_account_id=acct))

        # --- Transporte (4-5) ---
        for _ in range(rng.randint(4, 5)):
            merchant = rng.choice(POOLS["Transporte"])
            amount = 800 if "Bip" in merchant else rng.randrange(1500, 3200, 100)
            day = rng.randint(2, 27)
            add(tx(_utc(demo_year, month, day), amount, merchant, "expense", "Transporte",
                   financial_account_id=bci_id))

        # --- Golosinas (2-3) ---
        for _ in range(rng.randint(2, 3)):
            add(tx(_utc(demo_year, month, rng.randint(2, 27)), rng.randrange(1800, 4500, 100),
                   rng.choice(POOLS["Golosinas"]), "expense", "Golosinas", financial_account_id=tenpo_id))

        # --- Salud (occasional) ---
        if rng.random() < 0.6:
            add(tx(_utc(demo_year, month, rng.randint(5, 25)), rng.randrange(8000, 16000, 100),
                   rng.choice(POOLS["Salud"]), "expense", "Salud", financial_account_id=bci_id))

        # --- Ocio (occasional) ---
        if rng.random() < 0.7:
            add(tx(_utc(demo_year, month, rng.randint(8, 26)), rng.randrange(5000, 42000, 500),
                   rng.choice(POOLS["Ocio"]), "expense", "Ocio", financial_account_id=fala_id,
                   description="Salida con amigos"))

        # --- Compras online (occasional) ---
        if rng.random() < 0.6:
            add(tx(_utc(demo_year, month, rng.randint(6, 24)), rng.randrange(15000, 48000, 500),
                   rng.choice(POOLS["Compras online"]), "expense", "Compras online", financial_account_id=fala_id))

        # --- Transfers OUT (lending / splitting) ---
        if rng.random() < 0.8:
            target = rng.choice([camila, diego, andres])
            add(tx(_utc(demo_year, month, rng.randint(5, 25)), rng.randrange(8000, 35000, 1000),
                   f"Transferencia a {target.alias or target.name}", "transfer_out", "Transferencias",
                   financial_account_id=bci_id, counterparty=target.name, person_id=target.id,
                   description="Le presté / dividimos cuenta"))

        # --- Transfers IN (someone repaying) ---
        if rng.random() < 0.7:
            source = rng.choice([valentina, andres, camila])
            add(tx(_utc(demo_year, month, rng.randint(10, 27)), rng.randrange(8000, 30000, 1000),
                   source.name, "transfer_in", "Transferencias", financial_account_id=bci_id,
                   counterparty=source.name, person_id=source.id, description="Me devolvió plata"))

        # --- Investment monthly contribution (FMI) ---
        inv_tx = tx(_utc(demo_year, month, min(28, current_day_limit) if month == current_month else 28),
                    50000, "BCI Asset Management", "investment", "Inversiones",
                    description=f"Aporte mensual FMI {name}", financial_account_id=bci_id,
                    investment_account_id=inv_fmi_id)
        if in_month(inv_tx.occurred_at.month, inv_tx.occurred_at.day):
            all_txs.append(inv_tx)
            pending_moves.append((inv_tx, "deposit", 50000, inv_tx.occurred_at, f"Aporte {name}"))

        # --- Occasional brokerage contribution (Fintual) ---
        if month in (2, 4) :
            inv2 = tx(_utc(demo_year, month, 15), 30000, "Fintual", "investment", "Inversiones",
                      description=f"Aporte Risky Norris {name}", financial_account_id=bci_id,
                      investment_account_id=inv_fintual_id)
            all_txs.append(inv2)
            pending_moves.append((inv2, "deposit", 30000, inv2.occurred_at, f"Aporte {name}"))

    # --- A couple of "needs review" items in the last few days of the current month ---
    review_day_a = max(1, current_day_limit - 2)
    review_day_b = max(1, current_day_limit)
    all_txs.append(tx(_utc(demo_year, current_month, review_day_a), 15900, "Cargo desconocido online", "expense", "Por revisar",
                      financial_account_id=fala_id, status="needs_review", confidence=0.38,
                      description="Cargo no reconocido en tarjeta"))
    all_txs.append(tx(_utc(demo_year, current_month, review_day_b), 8400, "QPS *XZ", "expense", "Por revisar",
                      financial_account_id=fala_id, status="needs_review", confidence=0.41,
                      description="Comercio sin identificar"))

    # --- A disinvestment (withdrawal) a few months back for variety ---
    dis_tx = tx(_rel(3, 20), 40000, "Fintual", "disinvestment", "Desinversiones",
                description="Rescate parcial Risky Norris", financial_account_id=bci_id,
                investment_account_id=inv_fintual_id)
    all_txs.append(dis_tx)
    pending_moves.append((dis_tx, "withdrawal", 40000, dis_tx.occurred_at, "Rescate parcial"))

    # ------------------------------------------------------------------
    # Persist transactions, then splits + investment movements
    # ------------------------------------------------------------------
    session.add_all(all_txs)
    session.flush()

    for parent, parts in pending_splits:
        for category_name, amount, label in parts:
            session.add(TransactionSplit(
                transaction_id=parent.id,
                category_id=cat.get(category_name),
                amount=Decimal(str(amount)),
                currency="CLP",
                label=label,
            ))

    for parent, movement_type, amount, occurred_at, notes in pending_moves:
        session.add(InvestmentMovement(
            investment_account_id=parent.investment_account_id,
            transaction_id=parent.id,
            occurred_at=occurred_at,
            movement_type=movement_type,
            amount=Decimal(str(amount)),
            currency="CLP",
            source="manual",
            notes=notes,
        ))

    session.commit()
