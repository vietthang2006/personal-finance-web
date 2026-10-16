import hashlib
import logging
from datetime import date, datetime, timedelta, timezone

from dateutil.relativedelta import relativedelta
from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert

from app.core.database import SessionLocal
from app.models.account import Account
from app.models.recurring import RecurringTransaction
from app.models.system import Notification
from app.models.transaction import Transaction


logger = logging.getLogger(__name__)
MAX_CATCH_UP_OCCURRENCES = 100


def process_due_recurring_transactions(as_of: date | None = None) -> int:
    today = as_of or datetime.now(timezone.utc).date()
    created_count = 0
    with SessionLocal() as db:
        rules = list(
            db.scalars(
                select(RecurringTransaction)
                .where(
                    RecurringTransaction.status == "active",
                    RecurringTransaction.next_run_at <= today,
                )
                .order_by(RecurringTransaction.next_run_at)
                .limit(100)
                .with_for_update(skip_locked=True)
            ).all()
        )
        for rule in rules:
            occurrences = 0
            while rule.next_run_at <= today and occurrences < MAX_CATCH_UP_OCCURRENCES:
                run_date = rule.next_run_at
                delta = rule.amount if rule.kind == "income" else -rule.amount
                next_balance = Account.current_balance + delta
                can_apply = or_(
                    Account.allow_negative.is_(False) & (next_balance >= 0),
                    Account.allow_negative.is_(True)
                    & or_(Account.credit_limit.is_(None), next_balance >= -Account.credit_limit),
                )
                account_id = db.scalar(
                    update(Account)
                    .where(
                        Account.id == rule.account_id,
                        Account.user_id == rule.user_id,
                        can_apply,
                    )
                    .values(current_balance=Account.current_balance + delta)
                    .returning(Account.id)
                )
                if account_id is None:
                    rule.status = "paused"
                    db.execute(
                        insert(Notification)
                        .values(
                            user_id=rule.user_id,
                            kind="recurring_insufficient_funds",
                            title="Recurring transaction paused",
                            body=f"A scheduled transaction for {run_date.isoformat()} could not be applied.",
                            status="unread",
                            idempotency_key=f"recurring-insufficient:{rule.id}:{run_date.isoformat()}",
                        )
                        .on_conflict_do_nothing(index_elements=["user_id", "idempotency_key"])
                    )
                    logger.warning(
                        "Paused recurring rule %s because its scheduled amount could not be applied",
                        rule.id,
                    )
                    break

                dedup_hash = hashlib.sha256(
                    f"recurring:{rule.id}:{run_date.isoformat()}".encode("ascii")
                ).hexdigest()
                db.add(
                    Transaction(
                        user_id=rule.user_id,
                        account_id=rule.account_id,
                        kind=rule.kind,
                        category_id=rule.category_id,
                        subcategory_id=rule.subcategory_id,
                        amount=rule.amount,
                        transaction_date=run_date,
                        description=rule.description,
                        source="recurring",
                        dedup_hash=dedup_hash,
                    )
                )
                rule.last_generated_date = run_date
                rule.next_run_at = _next_occurrence(run_date, rule.frequency, rule.interval)
                occurrences += 1
                created_count += 1
                if rule.end_date is not None and rule.next_run_at > rule.end_date:
                    rule.status = "completed"
                    break
            if occurrences == MAX_CATCH_UP_OCCURRENCES and rule.next_run_at <= today:
                logger.warning("Recurring rule %s reached the catch-up limit", rule.id)
        db.commit()
    return created_count


def _next_occurrence(run_date: date, frequency: str, interval: int) -> date:
    if frequency == "daily":
        return run_date + timedelta(days=interval)
    if frequency == "weekly":
        return run_date + timedelta(weeks=interval)
    if frequency == "monthly":
        return run_date + relativedelta(months=interval)
    if frequency == "yearly":
        return run_date + relativedelta(years=interval)
    raise ValueError(f"Unsupported recurring frequency: {frequency}")
