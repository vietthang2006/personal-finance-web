import threading
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from uuid import UUID, uuid4

from sqlalchemy import text
from app.core.database import SessionLocal
from app.core.errors import AppError
from app.models.account import Account
from app.models.goal import GoalContribution, SavingsGoal
from app.models.system import Notification
from app.models.transaction import Transaction, TransactionCategory
from app.models.user import User
from app.schemas.goal import GoalContributionCreate
from app.services.goal_service import GoalService


class TestGoalConcurrency(unittest.TestCase):
    """
    Bộ kiểm thử tranh chấp đa luồng tổng quát (General Concurrency Test Suite) cho Module Mục tiêu tiết kiệm.
    Bao gồm:
      1. Kịch bản chung nhất: N luồng đồng thời tranh chấp Critical Section, đảm bảo tuần tự hóa (Serialization),
         không mất mát dữ liệu (No Lost Update), và từ chối chính xác các luồng vượt target (GOAL_OVER_TARGET).
      2. Kịch bản cán đích đồng thời: Đảm bảo chuyển trạng thái 'achieved' và tính Idempotency của Notification (BR-G06).
      3. Kịch bản tranh chấp cùng ví nguồn: Đảm bảo không âm ví (BR-A02), không xảy ra Deadlock (Anti-Deadlock Lock Ordering).
      4. Kịch bản Integration PostgreSQL thật (chạy khi có kết nối database).
    """

    def setUp(self) -> None:
        self.user_id = uuid4()
        self.user = User(
            id=self.user_id,
            email="concurrency_user@example.com",
            username="concurrency_user",
            default_currency="VND",
            timezone="Asia/Ho_Chi_Minh",
        )
        self.goal_id = uuid4()
        self.account_id = uuid4()
        self.category_saving = TransactionCategory(
            id=1, code="SAVING", kind="expense", name="Tiết kiệm"
        )

    # =========================================================================
    # KỊCH BẢN 1: TỔNG QUÁT HÓA TRANH CHẤP CRITICAL SECTION VÀ CHẶN NẠP QUÁ MỤC TIÊU
    # =========================================================================
    def test_general_concurrency_serialized_critical_section(self) -> None:
        """
        Kịch bản chung nhất:
        - Mục tiêu: Target = 100.000 VND, Current = 10.000 VND -> Khoảng trống còn lại R = 90.000 VND.
        - Số luồng N = 5 cùng xuất phát đồng thời qua threading.Barrier(5).
        - Mỗi luồng cùng gửi yêu cầu nạp M = 30.000 VND.
        - Vì R = 90.000 và M = 30.000, số luồng tối đa được phép thành công K = 90.000 / 30.000 = 3 luồng.
        - Đúng 3 luồng đầu tiên nạp thành công (201). Goal đạt đúng 100.000 VND và chuyển 'achieved'.
        - Đúng 2 luồng sau khi tới lượt kiểm tra thấy đã hết khoảng trống (hoặc goal đã achieved)
          sẽ bị từ chối sạch sẽ với 422 GOAL_OVER_TARGET (hoặc 409 GOAL_NOT_ACTIVE).
        - Kiểm tra tính toàn vẹn 4 bảng dữ liệu:
          + Số dư ví giảm đúng: 3 * 30.000 = 90.000 VND.
          + current_amount của mục tiêu đúng bằng 100.000 VND.
          + Đúng 3 bản ghi goal_contributions được tạo.
          + Đúng 3 transactions (source='goal') được ghi nhận.
        """
        target_amount = Decimal("100000.00")
        initial_current = Decimal("10.0000")  # 10.000
        contribution_amount = Decimal("30000.00")
        initial_balance = Decimal("200000.00")
        num_threads = 5

        # Trạng thái giả lập cơ sở dữ liệu dùng chung (Thread-safe DB State)
        db_lock = threading.Lock()
        goal_state = {
            "id": self.goal_id,
            "target_amount": target_amount,
            "current_amount": Decimal("10000.00"),
            "status": "active",
        }
        account_state = {
            "id": self.account_id,
            "balance": initial_balance,
        }
        contributions_recorded = []
        transactions_recorded = []

        barrier = threading.Barrier(num_threads)
        thread_results = []

        def worker(thread_idx: int):
            # Tạo instance service độc lập cho mỗi thread (như trong thực tế mỗi HTTP request có DI riêng)
            mock_db = Mock()
            mock_goal_repo = Mock()
            mock_account_repo = Mock()
            mock_category_repo = Mock()
            mock_transaction_repo = Mock()
            mock_notification_repo = Mock()
            mock_audit_repo = Mock()

            # Mô phỏng hành vi của SELECT ... FOR UPDATE trên Goal:
            # Luồng nào vào trước sẽ khóa hàng và đọc dữ liệu mới nhất đã commit của luồng trước.
            def thread_safe_get_goal_for_update(g_id, u_id):
                # Khi vào hàm này trong DB thật, Postgres giữ row lock cho tới khi commit/rollback.
                # Ta mô phỏng critical section bằng db_lock.
                db_lock.acquire()
                return SavingsGoal(
                    id=goal_state["id"],
                    user_id=self.user_id,
                    name="Quỹ du lịch",
                    target_amount=goal_state["target_amount"],
                    current_amount=goal_state["current_amount"],
                    status=goal_state["status"],
                )

            mock_goal_repo.get_for_update.side_effect = thread_safe_get_goal_for_update

            def thread_safe_get_account_for_update(a_id, u_id):
                return Mock(
                    id=account_state["id"],
                    user_id=self.user_id,
                    currency_code="VND",
                    is_archived=False,
                    current_balance=account_state["balance"],
                )

            mock_account_repo.get_for_update.side_effect = thread_safe_get_account_for_update
            mock_category_repo.get_system_by_code.return_value = self.category_saving

            def thread_safe_update_balance_atomic(acc_id, u_id, delta):
                if account_state["balance"] + delta >= Decimal("0.00"):
                    account_state["balance"] += delta
                    return account_state["balance"]
                return None

            mock_account_repo.update_balance_atomic.side_effect = thread_safe_update_balance_atomic

            def thread_safe_create_transaction(tx):
                transactions_recorded.append(tx)

            mock_transaction_repo.create_transaction.side_effect = thread_safe_create_transaction

            def thread_safe_add_contribution(cb):
                contributions_recorded.append(cb)

            mock_goal_repo.add_contribution.side_effect = thread_safe_add_contribution

            def thread_safe_increment_atomic(g_id, amount):
                # Kiểm tra constraint atomic: WHERE target_amount >= current_amount + amount
                if (
                    goal_state["status"] == "active"
                    and goal_state["current_amount"] + amount <= goal_state["target_amount"]
                ):
                    goal_state["current_amount"] += amount
                    if goal_state["current_amount"] >= goal_state["target_amount"]:
                        goal_state["status"] = "achieved"
                    return SavingsGoal(
                        id=goal_state["id"],
                        user_id=self.user_id,
                        name="Quỹ du lịch",
                        target_amount=goal_state["target_amount"],
                        current_amount=goal_state["current_amount"],
                        status=goal_state["status"],
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                return None

            mock_goal_repo.increment_current_atomic.side_effect = thread_safe_increment_atomic

            def thread_safe_commit():
                # Giải phóng row lock
                if db_lock.locked():
                    db_lock.release()

            def thread_safe_rollback():
                # Giải phóng row lock nếu lỗi
                if db_lock.locked():
                    db_lock.release()

            mock_db.commit.side_effect = thread_safe_commit
            mock_db.rollback.side_effect = thread_safe_rollback

            service = GoalService(
                db=mock_db,
                goal_repo=mock_goal_repo,
                account_repo=mock_account_repo,
                category_repo=mock_category_repo,
                transaction_repo=mock_transaction_repo,
                notification_repo=mock_notification_repo,
                audit_repo=mock_audit_repo,
                budget_service=Mock(),
            )

            # Đồng bộ tất cả 5 luồng cùng xuất phát đồng thời tại vạch xuất phát
            barrier.wait()

            payload = GoalContributionCreate(
                account_id=self.account_id,
                amount=contribution_amount,
            )

            try:
                resp = service.contribute(self.user, self.goal_id, payload)
                thread_results.append({"thread": thread_idx, "status": "success", "data": resp})
            except AppError as e:
                # Đảm bảo lock được giải phóng nếu service ném exception
                if db_lock.locked():
                    db_lock.release()
                thread_results.append(
                    {"thread": thread_idx, "status": "error", "code": e.code, "status_code": e.status_code}
                )
            except Exception as e:
                if db_lock.locked():
                    db_lock.release()
                thread_results.append({"thread": thread_idx, "status": "fatal", "error": str(e)})

        # Khởi chạy 5 luồng
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Đối soát kết quả
        successes = [r for r in thread_results if r["status"] == "success"]
        failures = [r for r in thread_results if r["status"] == "error"]

        # 1. ĐÚNG 3 luồng thành công (3 * 30.000 = 90.000)
        self.assertEqual(len(successes), 3, f"Expected 3 successes, got {len(successes)}")

        # 2. ĐÚNG 2 luồng thất bại và được từ chối an toàn với GOAL_OVER_TARGET hoặc GOAL_NOT_ACTIVE
        self.assertEqual(len(failures), 2, f"Expected 2 failures, got {len(failures)}")
        for f in failures:
            self.assertIn(
                f["code"],
                ["GOAL_OVER_TARGET", "GOAL_NOT_ACTIVE"],
                f"Unexpected error code: {f['code']}",
            )
            self.assertIn(f["status_code"], [409, 422])

        # 3. Đối soát bất biến 4 bảng:
        # Mục tiêu đạt chính xác 100.000 VND và trạng thái là achieved
        self.assertEqual(goal_state["current_amount"], Decimal("100000.00"))
        self.assertEqual(goal_state["status"], "achieved")

        # Ví nguồn bị trừ chính xác 90.000 VND (200.000 - 90.000 = 110.000)
        self.assertEqual(account_state["balance"], Decimal("110000.00"))

        # Bảng transactions có đúng 3 bản ghi
        self.assertEqual(len(transactions_recorded), 3)

        # Bảng goal_contributions có đúng 3 bản ghi
        self.assertEqual(len(contributions_recorded), 3)

    # =========================================================================
    # KỊCH BẢN 2: CÁN ĐÍCH ĐỒNG THỜI VÀ TÍNH IDEMPOTENT CỦA NOTIFICATION (BR-G06)
    # =========================================================================
    def test_concurrency_achieved_notification_idempotency(self) -> None:
        """
        Kịch bản: N = 5 luồng cùng nạp 50.000 VND vào mục tiêu Target = 100.000 VND (Current = 0).
        - Đúng K = 2 luồng thành công (2 * 50.000 = 100.000 VND).
        - Luồng thứ 2 cán đích 100% chuyển trạng thái 'achieved' và gửi thông báo chúc mừng.
        - Kiểm tra Idempotency Key: Chỉ DUY NHẤT 1 thông báo được tạo, không sinh trùng lặp thông báo.
        """
        num_threads = 5
        contribution_amount = Decimal("50000.00")
        target_amount = Decimal("100000.00")

        db_lock = threading.Lock()
        goal_state = {
            "id": self.goal_id,
            "target_amount": target_amount,
            "current_amount": Decimal("0.00"),
            "status": "active",
        }
        account_balance = [Decimal("500000.00")]
        created_notifications = []

        barrier = threading.Barrier(num_threads)
        thread_results = []

        def worker():
            mock_db = Mock()
            mock_goal_repo = Mock()
            mock_account_repo = Mock()
            mock_category_repo = Mock()
            mock_transaction_repo = Mock()
            mock_notification_repo = Mock()
            mock_audit_repo = Mock()

            def safe_get_goal(g_id, u_id):
                db_lock.acquire()
                return SavingsGoal(
                    id=goal_state["id"],
                    user_id=self.user_id,
                    name="Goal Idempotent",
                    target_amount=goal_state["target_amount"],
                    current_amount=goal_state["current_amount"],
                    status=goal_state["status"],
                )

            mock_goal_repo.get_for_update.side_effect = safe_get_goal
            mock_account_repo.get_for_update.return_value = Mock(
                id=self.account_id,
                user_id=self.user_id,
                currency_code="VND",
                is_archived=False,
                current_balance=account_balance[0],
            )
            mock_category_repo.get_system_by_code.return_value = self.category_saving
            mock_account_repo.update_balance_atomic.return_value = Decimal("450000.00")

            def safe_increment(g_id, amt):
                if (
                    goal_state["status"] == "active"
                    and goal_state["current_amount"] + amt <= goal_state["target_amount"]
                ):
                    goal_state["current_amount"] += amt
                    if goal_state["current_amount"] >= goal_state["target_amount"]:
                        goal_state["status"] = "achieved"
                    return SavingsGoal(
                        id=goal_state["id"],
                        user_id=self.user_id,
                        name="Goal Idempotent",
                        target_amount=goal_state["target_amount"],
                        current_amount=goal_state["current_amount"],
                        status=goal_state["status"],
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                return None

            mock_goal_repo.increment_current_atomic.side_effect = safe_increment

            # Mô phỏng kiểm tra idempotency_key trong notification_repo
            def safe_get_by_idempotency_key(u_id, idemp_key):
                for n in created_notifications:
                    if n.idempotency_key == idemp_key:
                        return n
                return None

            mock_notification_repo.get_by_idempotency_key.side_effect = safe_get_by_idempotency_key

            def safe_create_notif(notif):
                created_notifications.append(notif)

            mock_notification_repo.create.side_effect = safe_create_notif

            def release_lock():
                if db_lock.locked():
                    db_lock.release()

            mock_db.commit.side_effect = release_lock
            mock_db.rollback.side_effect = release_lock

            service = GoalService(
                db=mock_db,
                goal_repo=mock_goal_repo,
                account_repo=mock_account_repo,
                category_repo=mock_category_repo,
                transaction_repo=mock_transaction_repo,
                notification_repo=mock_notification_repo,
                audit_repo=mock_audit_repo,
                budget_service=Mock(),
            )

            barrier.wait()
            payload = GoalContributionCreate(account_id=self.account_id, amount=contribution_amount)

            try:
                res = service.contribute(self.user, self.goal_id, payload)
                thread_results.append(res)
            except AppError:
                if db_lock.locked():
                    db_lock.release()
            except Exception:
                if db_lock.locked():
                    db_lock.release()

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Kiểm tra: đúng 2 luồng thành công
        self.assertEqual(len(thread_results), 2)
        self.assertEqual(goal_state["current_amount"], Decimal("100000.00"))
        self.assertEqual(goal_state["status"], "achieved")

        # Kiểm tra: sinh đúng 1 notification duy nhất
        self.assertEqual(len(created_notifications), 1)
        self.assertEqual(created_notifications[0].kind, "goal_achieved")
        self.assertEqual(created_notifications[0].idempotency_key, f"goal_achieved:{self.goal_id}")

    # =========================================================================
    # KỊCH BẢN 3: ĐA LUỒNG TRANH CHẤP CÙNG 1 VÍ NGUỒN (CHẶN ÂM VÍ & TRÁNH DEADLOCK)
    # =========================================================================
    def test_concurrency_same_source_account_prevents_overdraft_and_deadlock(self) -> None:
        """
        Kịch bản: Ví nguồn chỉ có 100.000 VND.
        - N = 5 luồng cùng xuất phát đồng thời qua threading.Barrier(5) yêu cầu trích 40.000 VND.
        - Số tiền yêu cầu tổng cộng: 5 * 40.000 = 200.000 VND > 100.000 VND.
        - Đúng K = 2 luồng được phép thành công (2 * 40.000 = 80.000 VND).
        - Đúng 3 luồng sau bị từ chối sạch sẽ với 422 INSUFFICIENT_FUNDS.
        - Số dư ví cuối cùng đúng bằng 20.000 VND, không bao giờ bị âm (BR-A02).
        - Toàn bộ các thao tác khóa tài nguyên theo đúng trật tự (Goal -> Account), không bị Deadlock.
        """
        num_threads = 5
        contribution_amount = Decimal("40000.00")
        initial_balance = Decimal("100000.00")

        balance_lock = threading.Lock()
        account_balance = [initial_balance]

        def thread_safe_atomic_deduct(acc_id, u_id, delta):
            with balance_lock:
                if account_balance[0] + delta >= Decimal("0.00"):
                    account_balance[0] += delta
                    return account_balance[0]
                return None

        barrier = threading.Barrier(num_threads)
        results = []

        def worker():
            mock_db = Mock()
            mock_goal_repo = Mock()
            mock_account_repo = Mock()
            mock_category_repo = Mock()
            mock_transaction_repo = Mock()
            mock_notification_repo = Mock()
            mock_audit_repo = Mock()

            goal = SavingsGoal(
                id=self.goal_id,
                user_id=self.user_id,
                name="Goal",
                target_amount=Decimal("500000.00"),
                current_amount=Decimal("0.00"),
                status="active",
            )
            mock_goal_repo.get_for_update.return_value = goal
            mock_account_repo.get_for_update.return_value = Mock(
                id=self.account_id,
                user_id=self.user_id,
                currency_code="VND",
                is_archived=False,
                current_balance=account_balance[0],
            )
            mock_category_repo.get_system_by_code.return_value = self.category_saving
            mock_account_repo.update_balance_atomic.side_effect = thread_safe_atomic_deduct

            updated_g = SavingsGoal(
                id=self.goal_id,
                user_id=self.user_id,
                name="Goal",
                target_amount=Decimal("500000.00"),
                current_amount=Decimal("40000.00"),
                status="active",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            mock_goal_repo.increment_current_atomic.return_value = updated_g

            service = GoalService(
                db=mock_db,
                goal_repo=mock_goal_repo,
                account_repo=mock_account_repo,
                category_repo=mock_category_repo,
                transaction_repo=mock_transaction_repo,
                notification_repo=mock_notification_repo,
                audit_repo=mock_audit_repo,
                budget_service=Mock(),
            )

            barrier.wait()
            payload = GoalContributionCreate(account_id=self.account_id, amount=contribution_amount)

            try:
                res = service.contribute(self.user, self.goal_id, payload)
                results.append({"status": "success", "res": res})
            except AppError as e:
                results.append({"status": "error", "code": e.code, "status_code": e.status_code})

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        successes = [r for r in results if r["status"] == "success"]
        failures = [r for r in results if r["status"] == "error"]

        # 2 luồng thành công (2 * 40.000 = 80.000)
        self.assertEqual(len(successes), 2)
        # 3 luồng bị chặn vì hết tiền
        self.assertEqual(len(failures), 3)
        for f in failures:
            self.assertEqual(f["code"], "INSUFFICIENT_FUNDS")
            self.assertEqual(f["status_code"], 422)

        # Số dư còn lại đúng 20.000 VND
        self.assertEqual(account_balance[0], Decimal("20000.00"))

    # =========================================================================
    # KỊCH BẢN 4: KIỂM THỬ TRỰC TIẾP TRÊN POSTGRESQL ENGINE THẬT (INTEGRATION TEST)
    # =========================================================================
    def test_real_postgresql_concurrency_if_available(self) -> None:
        """
        Kiểm tra trực tiếp trên kết nối PostgreSQL thật (nếu có):
        - Tạo bản ghi thật trong bảng users, accounts, savings_goals.
        - Khởi chạy 5 threads với 5 SQLAlchemy Sessions độc lập cùng lúc gọi service.contribute().
        - Kiểm chứng PostgreSQL row-level lock 'SELECT ... FOR UPDATE' serialize trật tự thực thi.
        - Dọn dẹp sạch sẽ dữ liệu sau khi test xong.
        """
        try:
            # Kiểm tra xem có kết nối được tới DB không
            with SessionLocal() as check_session:
                check_session.execute(text("SELECT 1")).scalar()
        except Exception as e:
            self.skipTest(f"PostgreSQL connection is not accessible in this test runner: {e}")

        # Nếu kết nối được tới PostgreSQL, tiến hành test thật:
        test_user_id = uuid4()
        test_acc_id = uuid4()
        test_goal_id = uuid4()

        with SessionLocal() as db:
            # 1. Setup user
            u = User(
                id=test_user_id,
                email=f"pg_test_{test_user_id.hex[:8]}@example.com",
                username=f"pg_user_{test_user_id.hex[:8]}",
                password_hash="fakehash",
                default_currency="VND",
                timezone="Asia/Ho_Chi_Minh",
            )
            db.add(u)
            # 2. Setup account (balance = 200.000)
            acc = Account(
                id=test_acc_id,
                user_id=test_user_id,
                name="Ví Test PG",
                kind="cash",
                currency_code="VND",
                current_balance=Decimal("200000.00"),
                is_archived=False,
            )
            db.add(acc)
            # 3. Setup goal (target = 100.000, current = 10.000 -> remaining = 90.000)
            g = SavingsGoal(
                id=test_goal_id,
                user_id=test_user_id,
                name="Mục tiêu PG Test",
                target_amount=Decimal("100000.00"),
                current_amount=Decimal("10000.00"),
                status="active",
                deadline=date(2028, 1, 1),
            )
            db.add(g)
            db.commit()

        # N = 5 threads với 5 sessions riêng biệt
        num_threads = 5
        barrier = threading.Barrier(num_threads)
        real_results = []

        def real_worker(t_idx: int):
            from app.repositories.account_repository import AccountRepository
            from app.repositories.category_repository import CategoryRepository
            from app.repositories.goal_repository import GoalRepository
            from app.repositories.transaction_repository import TransactionRepository

            with SessionLocal() as thread_session:
                service = GoalService(
                    db=thread_session,
                    goal_repo=GoalRepository(thread_session),
                    account_repo=AccountRepository(thread_session),
                    category_repo=CategoryRepository(thread_session),
                    transaction_repo=TransactionRepository(thread_session),
                    notification_repo=Mock(),
                    audit_repo=Mock(),
                    budget_service=Mock(),
                )

                barrier.wait()
                payload = GoalContributionCreate(account_id=test_acc_id, amount=Decimal("30000.00"))

                try:
                    res = service.contribute(u, test_goal_id, payload)
                    real_results.append({"status": "success", "res": res})
                except AppError as e:
                    real_results.append({"status": "error", "code": e.code, "status_code": e.status_code})
                except Exception as e:
                    real_results.append({"status": "fatal", "error": str(e)})

        threads = [threading.Thread(target=real_worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        try:
            with SessionLocal() as db:
                db_goal = db.get(SavingsGoal, test_goal_id)
                db_acc = db.get(Account, test_acc_id)
                db_txs = (
                    db.query(Transaction)
                    .filter(Transaction.user_id == test_user_id, Transaction.source == "goal")
                    .all()
                )
                db_cbs = (
                    db.query(GoalContribution)
                    .filter(GoalContribution.goal_id == test_goal_id)
                    .all()
                )

                pg_successes = [r for r in real_results if r["status"] == "success"]
                pg_failures = [r for r in real_results if r["status"] == "error"]

                self.assertEqual(len(pg_successes), 3)
                self.assertEqual(len(pg_failures), 2)
                self.assertEqual(db_goal.current_amount, Decimal("100000.00"))
                self.assertEqual(db_goal.status, "achieved")
                self.assertEqual(db_acc.current_balance, Decimal("110000.00"))
                self.assertEqual(len(db_txs), 3)
                self.assertEqual(len(db_cbs), 3)
        finally:
            # Cleanup teardown
            with SessionLocal() as cleanup_db:
                cleanup_db.query(GoalContribution).filter(GoalContribution.goal_id == test_goal_id).delete()
                cleanup_db.query(Transaction).filter(Transaction.user_id == test_user_id).delete()
                cleanup_db.query(SavingsGoal).filter(SavingsGoal.id == test_goal_id).delete()
                cleanup_db.query(Account).filter(Account.id == test_acc_id).delete()
                cleanup_db.query(User).filter(User.id == test_user_id).delete()
                cleanup_db.commit()


if __name__ == "__main__":
    unittest.main()
