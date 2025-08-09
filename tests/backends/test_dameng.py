"""
Test Dameng-specific features
"""

from datetime import datetime, timedelta
from decimal import Decimal

from tortoise import Tortoise, fields
from tortoise.contrib import test
from tortoise.contrib.dameng.fields import IntervalField, RowIDField, XMLField
from tortoise.contrib.dameng.functions import (
    Decode,
    InitCap,
    Instr,
    ListAgg,
    LPad,
    NVL,
    RPad,
    RowNum,
    SysDate,
    ToChar,
    ToDate,
)
from tortoise.models import Model


class DamengTestModel(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=50)
    xml_data = XMLField(null=True)
    interval_data = IntervalField(null=True)
    row_id = RowIDField(null=True)
    created_at = fields.DatetimeField(null=True)
    status = fields.CharField(max_length=20, null=True)
    score = fields.IntField(null=True)
    category = fields.IntField(null=True)

    class Meta:
        app = "models"


class TestDameng(test.SimpleTestCase):
    async def asyncSetUp(self):
        if Tortoise._inited:
            await self._tearDownDB()
        self.db_config = test.getDBConfig(app_label="models", modules=[__name__])
        if self.db_config["connections"]["models"]["engine"] != "tortoise.backends.dameng":
            raise test.SkipTest("Dameng only")
        await Tortoise.init(self.db_config, _create_db=True)
        await Tortoise.generate_schemas()

    async def asyncTearDown(self) -> None:
        await Tortoise._drop_databases()
        await super().asyncTearDown()

    async def test_connection_params(self):
        """Test Dameng connection parameters"""
        conn = Tortoise.get_connection("models")
        self.assertEqual(conn.client_class.__name__, "DmClient")

    async def test_xml_field(self):
        """Test XMLField storage and retrieval"""
        xml_content = '<root><item id="1">Test</item></root>'
        obj = await DamengTestModel.create(
            name="test_xml",
            xml_data=xml_content
        )
        
        # Retrieve and verify
        loaded = await DamengTestModel.get(id=obj.id)
        self.assertEqual(loaded.xml_data, xml_content)

    async def test_interval_field(self):
        """Test IntervalField storage and retrieval"""
        interval = timedelta(hours=2, minutes=30, seconds=45)
        obj = await DamengTestModel.create(
            name="test_interval",
            interval_data=interval
        )
        
        # Retrieve and verify
        loaded = await DamengTestModel.get(id=obj.id)
        self.assertEqual(loaded.interval_data, interval)

    async def test_tochar_function(self):
        """Test ToChar function"""
        now = datetime.now()
        obj = await DamengTestModel.create(
            name="test_tochar",
            created_at=now
        )
        
        # Test date formatting
        result = await DamengTestModel.filter(id=obj.id).annotate(
            date_str=ToChar("created_at", "YYYY-MM-DD")
        ).values("date_str")
        
        self.assertEqual(result[0]["date_str"], now.strftime("%Y-%m-%d"))

    async def test_todate_function(self):
        """Test ToDate function"""
        date_str = "2024-01-15"
        
        # Create test data
        obj = await DamengTestModel.create(
            name="test_todate",
            created_at=datetime(2024, 1, 15)
        )
        
        # Test date parsing in filter
        result = await DamengTestModel.filter(
            created_at__gte=ToDate(date_str, "YYYY-MM-DD")
        ).count()
        
        self.assertEqual(result, 1)

    async def test_sysdate_function(self):
        """Test SysDate function"""
        # Create past and future records
        past = await DamengTestModel.create(
            name="past",
            created_at=datetime.now() - timedelta(days=1)
        )
        future = await DamengTestModel.create(
            name="future", 
            created_at=datetime.now() + timedelta(days=1)
        )
        
        # Filter using SysDate
        result = await DamengTestModel.filter(
            created_at__lte=SysDate()
        ).count()
        
        self.assertEqual(result, 1)  # Only past record

    async def test_initcap_function(self):
        """Test InitCap function"""
        await DamengTestModel.create(name="hello world")
        
        result = await DamengTestModel.annotate(
            capitalized=InitCap("name")
        ).values("capitalized")
        
        self.assertEqual(result[0]["capitalized"], "Hello World")

    async def test_instr_function(self):
        """Test Instr function"""
        await DamengTestModel.create(name="test@example.com")
        
        result = await DamengTestModel.annotate(
            at_pos=Instr("name", "@")
        ).values("at_pos")
        
        self.assertEqual(result[0]["at_pos"], 5)

    async def test_lpad_rpad_functions(self):
        """Test LPad and RPad functions"""
        await DamengTestModel.create(name="123")
        
        result = await DamengTestModel.annotate(
            left_padded=LPad("name", 5, "0"),
            right_padded=RPad("name", 5, "X")
        ).values("left_padded", "right_padded")
        
        self.assertEqual(result[0]["left_padded"], "00123")
        self.assertEqual(result[0]["right_padded"], "123XX")

    async def test_nvl_function(self):
        """Test NVL function"""
        # Create with NULL status
        await DamengTestModel.create(name="test_nvl", status=None)
        
        result = await DamengTestModel.annotate(
            status_with_default=NVL("status", "active")
        ).values("status_with_default")
        
        self.assertEqual(result[0]["status_with_default"], "active")

    async def test_decode_function(self):
        """Test Decode function"""
        await DamengTestModel.create(name="test1", category=1)
        await DamengTestModel.create(name="test2", category=2)
        await DamengTestModel.create(name="test3", category=3)
        
        result = await DamengTestModel.annotate(
            category_name=Decode(
                "category",
                1, "Basic",
                2, "Premium",
                3, "Enterprise",
                "Unknown"
            )
        ).values("category_name")
        
        categories = [r["category_name"] for r in result]
        self.assertIn("Basic", categories)
        self.assertIn("Premium", categories)
        self.assertIn("Enterprise", categories)

    async def test_rownum_function(self):
        """Test RowNum function"""
        # Create multiple records
        for i in range(20):
            await DamengTestModel.create(name=f"test_{i}")
        
        # Get first 10 using RowNum
        result = await DamengTestModel.filter(
            RowNum() <= 10
        ).count()
        
        self.assertEqual(result, 10)

    async def test_listagg_function(self):
        """Test ListAgg function"""
        # Create records in same category
        for i in range(3):
            await DamengTestModel.create(
                name=f"item_{i}",
                category=1
            )
        
        result = await DamengTestModel.filter(
            category=1
        ).annotate(
            names=ListAgg("name", ",")
        ).group_by("category").values("names")
        
        names = result[0]["names"].split(",")
        self.assertEqual(len(names), 3)
        self.assertIn("item_0", names)

    async def test_parameter_conversion(self):
        """Test parameter placeholder conversion"""
        # This tests the executor's parameter conversion
        results = await DamengTestModel.filter(
            name__in=["test1", "test2", "test3"]
        ).all()
        
        # Should work without errors
        self.assertIsInstance(results, list)

    async def test_connection_pool(self):
        """Test connection pool functionality"""
        conn = Tortoise.get_connection("models")
        
        # Test acquiring connections
        async with conn._pool.acquire() as connection:
            self.assertIsNotNone(connection)
        
        # Pool should still be healthy
        self.assertTrue(hasattr(conn._pool, "_queue"))

    async def test_transaction_rollback(self):
        """Test transaction rollback"""
        conn = Tortoise.get_connection("models")
        
        try:
            async with conn.in_transaction() as trans:
                await DamengTestModel.create(name="will_rollback")
                raise Exception("Force rollback")
        except Exception:
            pass
        
        # Record should not exist
        count = await DamengTestModel.filter(name="will_rollback").count()
        self.assertEqual(count, 0)

    async def test_bulk_operations(self):
        """Test bulk insert and update"""
        # Bulk create
        objs = [
            DamengTestModel(name=f"bulk_{i}", score=i)
            for i in range(100)
        ]
        await DamengTestModel.bulk_create(objs)
        
        # Verify
        count = await DamengTestModel.filter(name__startswith="bulk_").count()
        self.assertEqual(count, 100)
        
        # Bulk update
        await DamengTestModel.filter(
            name__startswith="bulk_"
        ).update(status="updated")
        
        updated = await DamengTestModel.filter(status="updated").count()
        self.assertEqual(updated, 100)

    async def test_decimal_precision(self):
        """Test decimal field precision"""
        # Create model with decimal field for testing
        class DecimalModel(Model):
            id = fields.IntField(primary_key=True)
            amount = fields.DecimalField(max_digits=10, decimal_places=4)
            
            class Meta:
                app = "models"
        
        await Tortoise.generate_schemas()
        
        # Test precise decimal
        value = Decimal("1234.5678")
        obj = await DecimalModel.create(amount=value)
        loaded = await DecimalModel.get(id=obj.id)
        
        self.assertEqual(loaded.amount, value)

    async def test_unique_constraint(self):
        """Test unique constraint enforcement"""
        # Create model with unique field
        class UniqueModel(Model):
            id = fields.IntField(primary_key=True)
            code = fields.CharField(max_length=20, unique=True)
            
            class Meta:
                app = "models"
        
        await Tortoise.generate_schemas()
        
        # Create first record
        await UniqueModel.create(code="UNIQUE001")
        
        # Try to create duplicate
        with self.assertRaises(Exception):  # IntegrityError
            await UniqueModel.create(code="UNIQUE001")

    async def test_index_creation(self):
        """Test index creation"""
        # Model with indexes
        class IndexedModel(Model):
            id = fields.IntField(primary_key=True)
            name = fields.CharField(max_length=50, index=True)
            category = fields.CharField(max_length=20)
            status = fields.CharField(max_length=20)
            
            class Meta:
                app = "models"
                indexes = [
                    ["category", "status"],  # Compound index
                ]
        
        await Tortoise.generate_schemas()
        
        # Create and query using indexed fields
        await IndexedModel.create(
            name="indexed",
            category="A",
            status="active"
        )
        
        # These queries should use indexes
        result = await IndexedModel.filter(name="indexed").exists()
        self.assertTrue(result)
        
        result = await IndexedModel.filter(
            category="A",
            status="active"
        ).exists()
        self.assertTrue(result)