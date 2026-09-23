import math
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.schemas.common import PaginationMeta


def paginate(
    db: Session, statement: Select[Any], page: int, page_size: int
) -> tuple[list[Any], PaginationMeta]:
    count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
    total = int(db.scalar(count_statement) or 0)
    items = list(db.scalars(statement.offset((page - 1) * page_size).limit(page_size)).unique())
    return items, PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        pages=math.ceil(total / page_size) if total else 0,
    )
