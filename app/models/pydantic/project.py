from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ProjectSyncRequest(BaseModel):
    project_key: str

class ProjectSyncResponse(BaseModel):
    project_key: str
    status: str
    issues_synced: int
    last_synced: datetime

class ProjectResponse(BaseModel):
    id: int
    key: str
    name: str
    description: Optional[str]
    last_synced: Optional[datetime]
    issues_count: int

class IssueResponse(BaseModel):
    key: str
    summary: str
    status: str
    priority: str
    assignee: str
    story_points: Optional[float]
    created_at: Optional[datetime]
