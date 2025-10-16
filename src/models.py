# src/models.py
from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError

class ActionItem(BaseModel):
    owner: Optional[str] = None
    task: str
    deadline: Optional[str] = Field(default=None, description="YYYY-MM-DD or null")

class ExtractedMeeting(BaseModel):
    date: Optional[str] = Field(default=None, description="YYYY-MM-DD or null")
    attendees: List[str]
    decisions: List[str]
    action_items: List[ActionItem]

class PackagedOutput(BaseModel):
    extracted: ExtractedMeeting
    summary: str
