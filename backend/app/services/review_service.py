"""
review_service.py — Business logic for player reviews.

Covers:
  - Eligibility check (booking must exist, belong to player, and be checked_in)
  - Duplicate review prevention (unique constraint on player_id + booking_id)
  - Review persistence
  - Efficient recalculation of field.average_rating and field.review_count via SQL AVG/COUNT
  - Paginated listing of reviews per field

Requirements: 13.1, 13.2, 13.3, 13.4
"""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.field import Field
from app.models.review import Review

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Submit a review  (Requirements 13.1, 13.2, 13.3)
# ---------------------------------------------------------------------------


async def submit_review(
    db: AsyncSession,
    player_id: UUID,
    field_id: UUID,
    booking_id: UUID,
    rating: int,
    review_text: str | None,
) -> Review:
    """
    Submit a rating and optional review text for a completed session.

    Eligibility rules:
      - The booking must exist and belong to player_id.
      - The booking's status must be "checked_in".
      - Only one review is allowed per (player_id, booking_id) pair.

    After persisting the review, field.average_rating and field.review_count
    are recalculated using a single SQL AVG + COUNT query for accuracy.

    Raises:
        HTTP 404  — booking not found
        HTTP 403  REVIEW_NOT_ELIGIBLE — booking doesn't belong to player or is not checked_in
        HTTP 409  DUPLICATE_REVIEW    — review already exists for this booking
        HTTP 404  — field not found (should not occur in practice due to FK constraints)

    Requirements: 13.1, 13.2, 13.3
    """
    # ── Verify booking exists, belongs to player, and is checked_in ──────
    booking_result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking: Booking | None = booking_result.scalar_one_or_none()

    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "BOOKING_NOT_FOUND", "message": "Booking not found."}},
        )

    if booking.player_id != player_id or booking.status != "checked_in":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "REVIEW_NOT_ELIGIBLE",
                    "message": (
                        "You can only review a booking that belongs to you "
                        "and has been checked in."
                    ),
                }
            },
        )

    # ── Persist the review (unique constraint guards duplicates) ─────────
    review = Review(
        player_id=player_id,
        field_id=field_id,
        booking_id=booking_id,
        rating=rating,
        review_text=review_text,
    )
    db.add(review)

    try:
        await db.flush()  # triggers the DB unique constraint check before commit
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "DUPLICATE_REVIEW",
                    "message": "You have already submitted a review for this booking.",
                }
            },
        )

    # ── Recalculate field rating stats via SQL AVG + COUNT ────────────────
    field_result = await db.execute(
        select(Field).where(Field.id == field_id)
    )
    field: Field | None = field_result.scalar_one_or_none()

    if field is not None:
        stats_result = await db.execute(
            select(func.avg(Review.rating), func.count(Review.id)).where(
                Review.field_id == field_id
            )
        )
        avg, count = stats_result.one()
        field.average_rating = round(float(avg), 2) if avg is not None else 0.0
        field.review_count = count

    await db.commit()
    await db.refresh(review)

    logger.info(
        "Review submitted: id=%s player=%s field=%s booking=%s rating=%s",
        review.id,
        player_id,
        field_id,
        booking_id,
        rating,
    )

    return review


# ---------------------------------------------------------------------------
# 2. List reviews for a field  (Requirement 13.4)
# ---------------------------------------------------------------------------


async def list_reviews(
    db: AsyncSession,
    field_id: UUID,
    page: int = 1,
    page_size: int = 10,
) -> list[Review]:
    """
    Return a paginated list of reviews for a field, ordered newest-first.

    Requirements: 13.4
    """
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Review)
        .where(Review.field_id == field_id)
        .order_by(Review.created_at.desc())
        .limit(page_size)
        .offset(offset)
    )
    return list(result.scalars().all())
