from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class JiraProject(Base):
    __tablename__ = "jira_projects"
    
    id = Column(Integer, primary_key=True, index=True)
    jira_key = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(500))
    is_active = Column(Boolean, default=True)
    last_synced = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    issues = relationship("JiraIssue", back_populates="project")
    sprints = relationship("JiraSprint", back_populates="project")


class JiraSprint(Base):
    __tablename__ = "jira_sprints"
    
    id = Column(Integer, primary_key=True, index=True)
    jira_id = Column(Integer, unique=True, index=True, nullable=False)
    project_id = Column(Integer, ForeignKey("jira_projects.id"))
    name = Column(String(255))
    state = Column(String(50))
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    project = relationship("JiraProject", back_populates="sprints")
    issues = relationship("JiraIssue", back_populates="sprint")


class JiraIssue(Base):
    __tablename__ = "jira_issues"
    
    id = Column(Integer, primary_key=True, index=True)
    jira_key = Column(String(50), unique=True, index=True, nullable=False)
    project_id = Column(Integer, ForeignKey("jira_projects.id"))
    sprint_id = Column(Integer, ForeignKey("jira_sprints.id"), nullable=True)
    
    summary = Column(String(500))
    description = Column(String(2000))
    status = Column(String(50))
    priority = Column(String(50))
    issue_type = Column(String(50))
    assignee = Column(String(255))
    assignee_email = Column(String(100))
    
    story_points = Column(Float, nullable=True)
    time_estimate = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    last_synced = Column(DateTime(timezone=True), server_default=func.now())
    custom_fields = Column(JSON, nullable=True)
    
    project = relationship("JiraProject", back_populates="issues")
    sprint = relationship("JiraSprint", back_populates="issues")
