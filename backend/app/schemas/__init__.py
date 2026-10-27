from app.schemas.auth import (
    PlayerRegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    UserBasic,
)
from app.schemas.field import (
    FieldCreate,
    FieldUpdate,
    FieldResponse,
    FieldSummary,
    SponsorshipPatch,
    FieldFilterParams,
    SlotSummary,
)
from app.schemas.slot import (
    SlotResponse,
    SlotGenerateRequest,
    SlotGenerateResponse,
    SlotStatusPatch,
    SlotUpdateMessage,
)
from app.schemas.booking import (
    BookingResponse,
    CheckInResponse,
    BookingVerifyResponse,
)
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionResponse,
    SlotChangeProposalCreate,
    SlotChangeProposalResponse,
    SlotChangeApproval,
    SubscriptionStatsResponse,
    SubscriptionStatsItem,
)
from app.schemas.review import ReviewCreate, ReviewResponse
from app.schemas.notification import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
)
from app.schemas.payment import (
    ChapaInitRequest,
    ChapaCheckoutResponse,
    ArifPayInitRequest,
    ArifPaySessionResponse,
)
from app.schemas.admin import (
    UserCreateByAdmin,
    UserUpdateByAdmin,
    AnalyticsResponse,
    DailyBookingCount,
    UserResponse,
)

__all__ = [
    # auth
    "PlayerRegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "RefreshRequest",
    "UserBasic",
    # field
    "FieldCreate",
    "FieldUpdate",
    "FieldResponse",
    "FieldSummary",
    "SponsorshipPatch",
    "FieldFilterParams",
    "SlotSummary",
    # slot
    "SlotResponse",
    "SlotGenerateRequest",
    "SlotGenerateResponse",
    "SlotStatusPatch",
    "SlotUpdateMessage",
    # booking
    "BookingResponse",
    "CheckInResponse",
    "BookingVerifyResponse",
    # subscription
    "SubscriptionCreate",
    "SubscriptionResponse",
    "SlotChangeProposalCreate",
    "SlotChangeProposalResponse",
    "SlotChangeApproval",
    "SubscriptionStatsResponse",
    "SubscriptionStatsItem",
    # review
    "ReviewCreate",
    "ReviewResponse",
    # notification
    "NotificationPreferenceResponse",
    "NotificationPreferenceUpdate",
    # payment
    "ChapaInitRequest",
    "ChapaCheckoutResponse",
    "ArifPayInitRequest",
    "ArifPaySessionResponse",
    # admin
    "UserCreateByAdmin",
    "UserUpdateByAdmin",
    "AnalyticsResponse",
    "DailyBookingCount",
    "UserResponse",
]
