from sqlalchemy import Column, Text, Date, ForeignKey, TIMESTAMP, timezone, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from data.db import Base

"""Representes an individual reported filer."""
class Member(Base):
    __tablename__ = "members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(Text, nullable=False)
    last_name = Column(Text, nullable=False)
    chamber = Column(Text, nullable=False)  # Senate / House
    party = Column(Text)
    filings = relationship("Filing", back_populates="member")

"""Representes an individual reported filing."""
class Filing(Base):
    __tablename__ = "filings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id = Column(UUID(as_uuid=True), ForeignKey("members.id", ondelete="CASCADE"))
    filing_type = Column(Text, nullable=False)
    filing_date = Column(Date, nullable=False)
    source = Column(Text, nullable=False)  # Senate / House
    scraped_at = Column(TIMESTAMP, default=datetime.now(timezone.utc))

    member = relationship("Member", back_populates="filings")
    trades = relationship("Trade", back_populates="filing", cascade="all, delete")

"""Representes a trade reported in a filing."""
class Trade(Base):
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filing_id = Column(UUID(as_uuid=True), ForeignKey("filings.id", ondelete="CASCADE"))
    transaction_date = Column(Date)
    owner = Column(Text)  # Self / Spouse / Child / Other
    asset_name = Column(Text)
    ticker = Column(Text)
    asset_type = Column(Text)  # Stock / ETF / Crypto / etc
    transaction_type = Column(Text)  # Purchase / Sale / Exchange
    amount_low = Column(Numeric)
    amount_high = Column(Numeric)

    filing = relationship("Filing", back_populates="trades")