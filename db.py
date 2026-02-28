import os
import time
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from models import Order

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./orders.db")

engine = sa.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
metadata = sa.MetaData()

orders_table = sa.Table(
    "orders",
    metadata,
    sa.Column("id", sa.String, primary_key=True),
    sa.Column("token_in", sa.String),
    sa.Column("token_out", sa.String),
    sa.Column("amount", sa.Float),
    sa.Column("order_type", sa.String),
    sa.Column("status", sa.String),
    sa.Column("tx_hash", sa.String, nullable=True),
    sa.Column("executed_price", sa.Float, nullable=True),
    sa.Column("created_at", sa.Float, default=time.time),
    sa.Column("last_error", sa.String, nullable=True),
)

logs_table = sa.Table(
    "order_logs",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("order_id", sa.String),
    sa.Column("level", sa.String),
    sa.Column("message", sa.String),
    sa.Column("ts", sa.Float, default=time.time),
)

metadata.create_all(engine)
Session = sessionmaker(bind=engine, expire_on_commit=False)
