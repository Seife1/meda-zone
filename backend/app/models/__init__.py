# Import all ORM models so they register with Base.metadata.
# This ensures Alembic autogenerate picks up every table.

from app.models.user import User
from app.models.field import Field
from app.models.slot import Slot
from app.models.subscription import Subscription
from app.models.booking import Booking
from app.models.slot_change_proposal import SlotChangeProposal
from app.models.review import Review
from app.models.notification_preference import NotificationPreference

__all__ = [
    "User",
    "Field",
    "Slot",
    "Subscription",
    "Booking",
    "SlotChangeProposal",
    "Review",
    "NotificationPreference",
]
