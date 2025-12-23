from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[str] = Field(None, pattern="^(draft|in_progress|completed)$")

class ProjectResponse(ProjectBase):
    id: str
    user_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    chapter_count: int = 0
    word_count: int = 0
    
    class Config:
        orm_mode = True

class ProjectList(BaseModel):
    projects: List[ProjectResponse]
    total: int
    skip: int
    limit: int 