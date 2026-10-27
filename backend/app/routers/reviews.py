"""
Reviews router — submit and list field reviews.

Routes:
  POST  /reviews                   — authenticated player; submit rating + review text
  GET   /fields/{field_id}/reviews — public; paginated reviews for a field

Requirements: 13.1, 13.2, 13.3, 13.4
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewResponse
from app.services import review_service
from app.services.auth_service import get_current_user

router = APIRouter(tags=["Reviews"])


# ---------------------------------------------------------------------------
# POST /reviews — submit a review  (Requirements 13.1, 13.2, 13.3)
# ---------------------------------------------------------------------------


@router.post(
    "/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a review for a completed session",
    description=(
        "Authenticated player submits a rating (1–5) and optional text for a "
        "booking that has been checked in. One review allowed per booking."
    ),
)
async def submit_review(
    body: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    review = await review_service.submit_review(
        db=db,
        player_id=current_user.id,
        field_id=body.field_id,
        booking_id=body.booking_id,
        rating=body.rating,
        review_text=body.review_text,
    )
    return ReviewResponse.model_validate(review)


# ---------------------------------------------------------------------------
# GET /fields/{field_id}/reviews — list reviews for a field  (Requirement 13.4)
# ---------------------------------------------------------------------------


@router.get(
    "/fields/{field_id}/reviews",
    response_model=list[ReviewResponse],
    summary="List paginated reviews for a field",
    description=(
        "Public endpoint. Returns reviews for the given field ordered newest-first. "
        "Supports pagination via page and page_size query parameters."
    ),
)
async def list_field_reviews(
    field_id: UUID,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=100, description="Reviews per page"),
    db: AsyncSession = Depends(get_db),
) -> list[ReviewResponse]:
    reviews = await review_service.list_reviews(
        db=db,
        field_id=field_id,
        page=page,
        page_size=page_size,
    )
    return [ReviewResponse.model_validate(r) for r in reviews]
