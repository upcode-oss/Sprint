from app.db.base import Base
from app.instance_link import LinkColumns


class InstanceConnection(LinkColumns, Base):
    __tablename__ = "instance_connections"
