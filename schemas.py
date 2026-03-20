"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# --- User Schemas ---
class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    solved_count: int
    total_submissions: int

    class Config:
        from_attributes = True


# --- Problem Schemas ---
class TestCaseCreate(BaseModel):
    input_data: str
    expected_output: str
    is_sample: bool = False


class ProblemCreate(BaseModel):
    code: str
    title: str
    description: str
    input_description: str = ""
    output_description: str = ""
    sample_input: str = ""
    sample_output: str = ""
    difficulty: str = "Easy"
    time_limit: float = 1.0
    memory_limit: int = 256
    testcases: List[TestCaseCreate] = []


class ProblemResponse(BaseModel):
    id: int
    code: str
    title: str
    description: str
    input_description: str
    output_description: str
    sample_input: str
    sample_output: str
    difficulty: str
    time_limit: float
    memory_limit: int
    total_submissions: int
    accepted_count: int

    class Config:
        from_attributes = True


# --- Submission Schemas ---
class SubmissionCreate(BaseModel):
    problem_id: int
    language: str
    source_code: str


class SubmissionResponse(BaseModel):
    id: int
    problem_id: int
    language: str
    status: str
    score: float
    time_ms: float
    memory_kb: float
    created_at: datetime

    class Config:
        from_attributes = True
