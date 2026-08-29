from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class RecommendationStatus(str, enum.Enum):
    NEW = "NEW"
    APPLIED = "APPLIED"
    DISMISSED = "DISMISSED"
    ERROR = "ERROR"


class AnalyticsHistory(Base):
    __tablename__ = "analytics_history"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("jira_projects.id"))
    sprint_id = Column(Integer, ForeignKey("jira_sprints.id"), nullable=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    
    velocity = Column(Float, nullable=True)
    completion_rate = Column(Float, nullable=True)
    load_index = Column(Float, nullable=True)
    blocked_count = Column(Integer, default=0)
    wip_count = Column(Integer, default=0)
    total_issues = Column(Integer, default=0)
    completed_issues = Column(Integer, default=0)
    
    metrics = Column(JSON, nullable=True)
    
    project = relationship("JiraProject", back_populates="analytics")
    recommendations = relationship("AIRecommendation", back_populates="analytics")


class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("jira_projects.id"))
    analytics_id = Column(Integer, ForeignKey("analytics_history.id"), nullable=True)
    
    title = Column(String(255), nullable=False)
    description = Column(String(2000))
    impact = Column(String(50))
    category = Column(String(50))
    action = Column(JSON)
    
    jira_issue_created = Column(String(50), nullable=True)
    status = Column(SQLEnum(RecommendationStatus), default=RecommendationStatus.NEW)
    user_rating = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    project = relationship("JiraProject", back_populates="recommendations")
    analytics = relationship("AnalyticsHistory", back_populates="recommendations")