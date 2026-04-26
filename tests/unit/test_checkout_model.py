from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from asset_hub.models.asset import Asset
from asset_hub.models.asset_type import AssetType
from asset_hub.models.checkout import CheckoutRecord


def _make_asset(session: Session) -> Asset:
    t = AssetType(name="T", code_prefix="TST", custom_fields=[])
    session.add(t)
    session.flush()
    a = Asset(asset_code="TST-001", name="A", type_id=t.id, custom_data={})
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def test_checkout_record_can_be_persisted(session: Session):
    a = _make_asset(session)
    rec = CheckoutRecord(
        asset_id=a.id,
        holder="张三",
        location="工位 5",
        checkout_note="借用一周",
    )
    session.add(rec)
    session.commit()
    session.refresh(rec)

    assert rec.id is not None
    assert rec.returned_at is None
    assert isinstance(rec.checked_out_at, datetime)


def test_partial_unique_index_blocks_second_open_checkout(session: Session):
    a = _make_asset(session)
    session.add(CheckoutRecord(asset_id=a.id, holder="张三"))
    session.commit()

    session.add(CheckoutRecord(asset_id=a.id, holder="李四"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_closed_checkout_allows_new_open_checkout(session: Session):
    a = _make_asset(session)
    first = CheckoutRecord(asset_id=a.id, holder="张三")
    session.add(first)
    session.commit()

    first.returned_at = datetime.now(UTC)
    session.add(first)
    session.commit()

    session.add(CheckoutRecord(asset_id=a.id, holder="李四"))
    session.commit()  # 不应抛异常
