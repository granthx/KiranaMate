"""
Seed demo data for KiranaMate hackathon demo
Run: python db/seed.py
"""
import asyncio
import uuid
from datetime import datetime, timedelta
import random
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from db.models import Base, Merchant, Customer, Transaction, KhataEntry, InventoryItem, SalesBaseline
from dotenv import load_dotenv

load_dotenv()

from db.database import engine, AsyncSessionLocal

MERCHANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")

CUSTOMERS = [
    {"name": "Mohan Sharma",   "phone": "9811001001", "segment": "regular",    "avg_spend": 450, "pay_behavior": "delayed",  "warmth": 0.7},
    {"name": "Sunita Devi",    "phone": "9811001002", "segment": "regular",    "avg_spend": 320, "pay_behavior": "delayed",  "warmth": 0.8},
    {"name": "Ramesh Gupta",   "phone": "9811001003", "segment": "vip",        "avg_spend": 820, "pay_behavior": "delayed",  "warmth": 0.9},
    {"name": "Priya Jain",     "phone": "9811001004", "segment": "vip",        "avg_spend": 650, "pay_behavior": "on_time",  "warmth": 0.85},
    {"name": "Vijay Kumar",    "phone": "9811001005", "segment": "regular",    "avg_spend": 280, "pay_behavior": "on_time",  "warmth": 0.75},
    {"name": "Anjali Singh",   "phone": "9811001006", "segment": "occasional", "avg_spend": 150, "pay_behavior": "on_time",  "warmth": 0.6},
    {"name": "Deepak Verma",   "phone": "9811001007", "segment": "regular",    "avg_spend": 390, "pay_behavior": "on_time",  "warmth": 0.7},
    {"name": "Kavita Yadav",   "phone": "9811001008", "segment": "occasional", "avg_spend": 210, "pay_behavior": "on_time",  "warmth": 0.65},
]

INVENTORY = [
    {"sku": "SKU-D001", "name": "Amul Toned Milk 500ml",     "cat": "dairy",    "qty": 87,  "cost": 22, "price": 30,  "margin": 18, "expiry_days": 2},
    {"sku": "SKU-D002", "name": "Amul Paneer 200g",           "cat": "dairy",    "qty": 43,  "cost": 55, "price": 68,  "margin": 15, "expiry_days": 3},
    {"sku": "SKU-D003", "name": "Mother Dairy Curd 400g",     "cat": "dairy",    "qty": 31,  "cost": 35, "price": 42,  "margin": 12, "expiry_days": 3},
    {"sku": "SKU-D004", "name": "Amul Butter 100g",           "cat": "dairy",    "qty": 24,  "cost": 45, "price": 56,  "margin": 14, "expiry_days": 15},
    {"sku": "SKU-S001", "name": "Aashirvaad Atta 5kg",        "cat": "staples",  "qty": 22,  "cost": 240,"price": 280, "margin": 9,  "expiry_days": 60},
    {"sku": "SKU-S002", "name": "Tata Salt 1kg",              "cat": "staples",  "qty": 48,  "cost": 18, "price": 24,  "margin": 20, "expiry_days": 365},
    {"sku": "SKU-S003", "name": "Fortune Sunflower Oil 1L",   "cat": "staples",  "qty": 30,  "cost": 130,"price": 155, "margin": 14, "expiry_days": 180},
    {"sku": "SKU-SN001","name": "Maggi 2-Min Noodles 70g",    "cat": "snacks",   "qty": 120, "cost": 12, "price": 15,  "margin": 16, "expiry_days": 90},
    {"sku": "SKU-SN002","name": "Lay's Classic Salted 26g",   "cat": "snacks",   "qty": 80,  "cost": 8,  "price": 10,  "margin": 20, "expiry_days": 60},
    {"sku": "SKU-B001", "name": "Coca Cola 600ml",            "cat": "beverages","qty": 60,  "cost": 28, "price": 40,  "margin": 25, "expiry_days": 120},
    {"sku": "SKU-PC001","name": "Surf Excel 1kg",             "cat": "personal_care","qty":48,"cost":185,"price": 220, "margin": 14, "expiry_days": 730},
    {"sku": "SKU-PC002","name": "Dove Soap 100g",             "cat": "personal_care","qty":35,"cost": 40,"price": 52,  "margin": 18, "expiry_days": 730},
]

CATEGORIES = ["dairy", "snacks", "staples", "beverages", "personal_care"]

def random_amount(category: str) -> float:
    ranges = {
        "dairy":        (30, 280),
        "snacks":       (10, 80),
        "staples":      (20, 400),
        "beverages":    (20, 120),
        "personal_care":(40, 220),
    }
    lo, hi = ranges.get(category, (20, 200))
    return round(random.uniform(lo, hi), 2)


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables created")

    async with AsyncSessionLocal() as session:
        # ── Merchant ──────────────────────────────────
        merchant = Merchant(
            id=MERCHANT_ID,
            name="Ramesh Kumar Sharma",
            shop_name="Sharma General Store",
            phone="9810000001",
            address="Shop No. 14, Laxmi Nagar Market",
            pin_code="110092",
            city="Delhi",
            paytm_mid="DEMO_PAYTM_MID_001",
            language="hi",
            autonomous_mode=False,
        )
        session.add(merchant)
        await session.flush()
        print("✅ Merchant created")

        # ── Customers ─────────────────────────────────
        customer_ids = []
        for c in CUSTOMERS:
            cust = Customer(
                merchant_id=MERCHANT_ID,
                name=c["name"],
                phone=c["phone"],
                segment=c["segment"],
                avg_spend=c["avg_spend"],
                pay_behavior=c["pay_behavior"],
                warmth_score=c["warmth"],
                last_txn_at=datetime.utcnow() - timedelta(days=random.randint(1, 7)),
            )
            session.add(cust)
            await session.flush()
            customer_ids.append(cust.id)
        print(f"✅ {len(CUSTOMERS)} customers created")

        # ── Inventory ─────────────────────────────────
        for item in INVENTORY:
            inv = InventoryItem(
                merchant_id=MERCHANT_ID,
                sku_id=item["sku"],
                name=item["name"],
                category=item["cat"],
                quantity=item["qty"],
                unit_cost=item["cost"],
                selling_price=item["price"],
                margin_pct=item["margin"],
                expiry_date=datetime.utcnow() + timedelta(days=item["expiry_days"]),
            )
            session.add(inv)
        print(f"✅ {len(INVENTORY)} inventory items created")

        # ── Transactions (last 30 days) ───────────────
        txn_count = 0
        now = datetime.utcnow()
        for day_offset in range(30):
            txn_date = now - timedelta(days=day_offset)
            day_of_week = txn_date.weekday()  # 0=Mon, 6=Sun

            # Peak hours: 9-11 AM and 6-8 PM
            hours = list(range(8, 22))
            for _ in range(random.randint(40, 90)):
                hour = random.choices(
                    hours,
                    weights=[1,3,4,3,2,2,2,2,1,3,4,3,2,1],
                    k=1
                )[0]
                category = random.choices(
                    CATEGORIES,
                    weights=[25, 20, 25, 15, 15],  # dairy & staples dominant
                    k=1
                )[0]

                # Simulate today's dairy anomaly (day_offset=0, Wednesday)
                if day_offset == 0 and category == "dairy":
                    if random.random() < 0.60:  # drop 60% of dairy txns today
                        continue

                txn = Transaction(
                    merchant_id=MERCHANT_ID,
                    txn_id=f"TXN{uuid.uuid4().hex[:12].upper()}",
                    amount=random_amount(category),
                    category=category,
                    sku_id=random.choice([i["sku"] for i in INVENTORY if i["cat"] == category or True]),
                    payment_mode=random.choices(["upi", "cash", "card"], weights=[70, 25, 5], k=1)[0],
                    customer_id=random.choice(customer_ids) if random.random() < 0.4 else None,
                    txn_time=txn_date.replace(hour=hour, minute=random.randint(0, 59)),
                )
                session.add(txn)
                txn_count += 1
        print(f"✅ {txn_count} transactions created (last 30 days)")

        # ── Khata Entries (overdue) ───────────────────
        khata_data = [
            {"cust_idx": 0, "amount": 420,  "desc": "Dairy items - Invoice #1042",  "days_ago": 8},
            {"cust_idx": 1, "amount": 1240, "desc": "Weekly groceries - Invoice #1038", "days_ago": 5},
            {"cust_idx": 2, "amount": 2540, "desc": "Bulk order - Invoice #1029",    "days_ago": 12},
        ]
        for k in khata_data:
            entry = KhataEntry(
                merchant_id=MERCHANT_ID,
                customer_id=customer_ids[k["cust_idx"]],
                amount=k["amount"],
                description=k["desc"],
                due_date=datetime.utcnow() - timedelta(days=k["days_ago"] - 2),
                status="pending",
                reminder_count=0,
            )
            session.add(entry)
        print("✅ 3 overdue khata entries created")

        # ── Sales Baselines (4-week averages) ─────────
        for cat in CATEGORIES:
            for dow in range(7):
                for hour in range(8, 22):
                    baseline = SalesBaseline(
                        merchant_id=MERCHANT_ID,
                        category=cat,
                        day_of_week=dow,
                        hour=hour,
                        avg_revenue=random_amount(cat) * random.uniform(3, 8),
                        stddev=random.uniform(50, 200),
                        sample_count=4,
                    )
                    session.add(baseline)
        print("✅ Sales baselines seeded (4-week rolling averages)")

        await session.commit()

    print("\n🎉 Demo data seeded successfully!")
    print(f"   Merchant ID: {MERCHANT_ID}")
    print("   Phone (WhatsApp trigger): 9810000001")
    print("   3 overdue khata entries ready")
    print("   Dairy anomaly simulated for today")
    print("\nRun the API: uvicorn api.main:app --reload")


if __name__ == "__main__":
    asyncio.run(seed())
