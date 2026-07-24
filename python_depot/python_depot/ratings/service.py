"""Rating and review service — CRUD operations and moderation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from python_depot.pydepot.models import Package
from python_depot.ratings.models import Rating, Review


class RatingService:
    """Handles ratings, reviews, and moderation.

    Provides CRUD operations for user ratings (1-5 stars) and reviews
    with a simple moderation queue (pending / approved / rejected).
    """

    def __init__(self, db: Session) -> None:
        """Initialize with a database session.

        Args:
            db: SQLAlchemy synchronous session.
        """
        self.db = db

    def submit_rating(
        self, package_name: str, user_id: str, score: int
    ) -> dict[str, Any]:
        """Submit or update a rating for a package.

        Args:
            package_name: Name of the package.
            user_id: User identifier.
            score: Rating score (1-5).

        Returns:
            Response dict with rating info.
        """
        pkg = self.db.query(Package).filter(Package.name == package_name).first()
        if pkg is None:
            return {"error": "package_not_found", "package": package_name}

        if not 1 <= score <= 5:
            return {"error": "invalid_score", "score": score}

        existing = (
            self.db.query(Rating)
            .filter(Rating.package_id == pkg.id, Rating.user_id == user_id)
            .first()
        )
        if existing:
            existing.score = score
            existing.created_at = datetime.now(UTC)
            self.db.commit()
            return {"package": package_name, "status": "rated", "score": score}

        rating = Rating(package_id=pkg.id, user_id=user_id, score=score)
        self.db.add(rating)
        self.db.commit()
        return {"package": package_name, "status": "rated", "score": score}

    def get_ratings(self, package_name: str) -> dict[str, Any]:
        """Get all ratings for a package.

        Args:
            package_name: Name of the package.

        Returns:
            Response dict with ratings list and average.
        """
        pkg = self.db.query(Package).filter(Package.name == package_name).first()
        if pkg is None:
            return {"package": package_name, "ratings": [], "average": 0.0}

        ratings = self.db.query(Rating).filter(Rating.package_id == pkg.id).all()
        if not ratings:
            return {"package": package_name, "ratings": [], "average": 0.0}

        avg = sum(r.score for r in ratings) / len(ratings)
        return {
            "package": package_name,
            "ratings": [{"user_id": r.user_id, "score": r.score} for r in ratings],
            "average": round(avg, 2),
        }

    def rating_summary(self, package_name: str) -> dict[str, Any]:
        """Get rating distribution for a package.

        Args:
            package_name: Name of the package.

        Returns:
            Response dict with distribution.
        """
        pkg = self.db.query(Package).filter(Package.name == package_name).first()
        dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

        if pkg is not None:
            ratings = self.db.query(Rating).filter(Rating.package_id == pkg.id).all()
            for r in ratings:
                if 1 <= r.score <= 5:
                    dist[r.score] += 1

        return {"package": package_name, "distribution": dist}

    def submit_review(
        self, package_name: str, user_id: str, title: str, body: str
    ) -> dict[str, Any]:
        """Submit a review for a package (goes to moderation queue).

        Args:
            package_name: Name of the package.
            user_id: User identifier.
            title: Review title.
            body: Review body text.

        Returns:
            Response dict with review info.
        """
        pkg = self.db.query(Package).filter(Package.name == package_name).first()
        if pkg is None:
            return {"error": "package_not_found", "package": package_name}

        review = Review(
            package_id=pkg.id,
            user_id=user_id,
            title=title,
            body=body,
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return {"package": package_name, "status": "reviewed", "review_id": review.id}

    def list_reviews(
        self, package_name: str, status: str | None = None
    ) -> dict[str, Any]:
        """List reviews for a package, optionally filtered by moderation status.

        Args:
            package_name: Name of the package.
            status: Optional moderation status filter.

        Returns:
            Response dict with reviews list.
        """
        pkg = self.db.query(Package).filter(Package.name == package_name).first()
        if pkg is None:
            return {"package": package_name, "reviews": [], "total": 0}

        query = self.db.query(Review).filter(Review.package_id == pkg.id)
        if status:
            query = query.filter(Review.moderation_status == status)
        reviews = query.all()
        return {
            "package": package_name,
            "reviews": [
                {
                    "id": r.id,
                    "title": r.title,
                    "user_id": r.user_id,
                    "status": r.moderation_status,
                }
                for r in reviews
            ],
            "total": len(reviews),
        }

    def get_review(self, package_name: str, review_id: int) -> dict[str, Any]:
        """Get a specific review.

        Args:
            package_name: Name of the package.
            review_id: Review ID.

        Returns:
            Response dict with review info.
        """
        review = self.db.query(Review).filter(Review.id == review_id).first()
        if review is None:
            return {"package": package_name, "review_id": review_id, "found": False}
        return {
            "package": package_name,
            "review_id": review.id,
            "found": True,
            "title": review.title,
            "body": review.body,
            "user_id": review.user_id,
            "status": review.moderation_status,
        }

    def moderate_review(self, review_id: int, action: str) -> dict[str, Any]:
        """Approve or reject a review.

        Args:
            review_id: Review ID.
            action: 'approve' or 'reject'.

        Returns:
            Response dict with moderation result.
        """
        review = self.db.query(Review).filter(Review.id == review_id).first()
        if review is None:
            return {"error": "review_not_found"}

        if action not in ("approve", "reject"):
            return {"error": "invalid_action"}

        review.moderation_status = "approved" if action == "approve" else "rejected"
        review.moderated_at = datetime.now(UTC)
        self.db.commit()
        return {"review_id": review_id, "status": review.moderation_status}
