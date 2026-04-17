import uuid

from sqlmodel import Session, select

from asset_hub.models.checkout import CheckoutRecord


class CheckoutRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, record: CheckoutRecord) -> CheckoutRecord:
        self.session.add(record)
        self.session.flush()
        return record

    def find_open_by_asset(self, asset_id: uuid.UUID) -> CheckoutRecord | None:
        stmt = (
            select(CheckoutRecord)
            .where(CheckoutRecord.asset_id == asset_id)
            .where(CheckoutRecord.returned_at.is_(None))
        )
        return self.session.exec(stmt).first()

    def list_by_asset(self, asset_id: uuid.UUID) -> list[CheckoutRecord]:
        stmt = (
            select(CheckoutRecord)
            .where(CheckoutRecord.asset_id == asset_id)
            .order_by(CheckoutRecord.checked_out_at.desc())
        )
        return list(self.session.exec(stmt).all())
