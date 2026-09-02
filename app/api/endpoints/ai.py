from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.sqlalchemy.user import User
from app.models.sqlalchemy.jira import JiraProject
from app.models.sqlalchemy.analytics import AIRecommendation, RecommendationStatus
from app.services.ai_recommendation_service import AIRecommendationService

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/recommendations/{project_key}/generate")
async def generate_recommendations(
    project_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(JiraProject).filter(JiraProject.jira_key == project_key).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    service = AIRecommendationService()
    recommendations = service.generate_recommendations(project_key)
    
    return {
        "project": project_key,
        "recommendations": recommendations,
        "count": len(recommendations)
    }


@router.get("/recommendations/{project_key}")
async def get_recommendations(
    project_key: str,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(JiraProject).filter(JiraProject.jira_key == project_key).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    recommendations = db.query(AIRecommendation).filter(
        AIRecommendation.project_id == project.id
    ).order_by(AIRecommendation.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "impact": r.impact,
            "category": r.category,
            "status": r.status.value if r.status else None,
            "user_rating": r.user_rating,
            "created_at": r.created_at
        }
        for r in recommendations
    ]


@router.post("/recommendations/{recommendation_id}/rate")
async def rate_recommendation(
    recommendation_id: int,
    rating: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if rating < 1 or rating > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 1 and 5"
        )
    
    recommendation = db.query(AIRecommendation).filter(
        AIRecommendation.id == recommendation_id
    ).first()
    
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )
    
    recommendation.user_rating = rating
    db.commit()
    
    return {
        "message": "Rating saved",
        "rating": rating
    }


@router.post("/recommendations/{recommendation_id}/apply")
async def apply_recommendation(
    recommendation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    recommendation = db.query(AIRecommendation).filter(
        AIRecommendation.id == recommendation_id
    ).first()
    
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )
    
    recommendation.status = RecommendationStatus.APPLIED
    db.commit()
    
    return {
        "message": "Recommendation marked as applied",
        "id": recommendation_id
    }