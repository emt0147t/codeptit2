"""
SQLAlchemy models for the Online Judge.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, Float, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from database import Base
import enum


class SubmissionStatus(str, enum.Enum):
    PENDING = "Pending"
    ACCEPTED = "Accepted"
    WRONG_ANSWER = "Wrong Answer"
    TIME_LIMIT = "Time Limit Exceeded"
    MEMORY_LIMIT = "Memory Limit Exceeded"
    RUNTIME_ERROR = "Runtime Error"
    COMPILE_ERROR = "Compilation Error"


class Difficulty(str, enum.Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Stats
    solved_count = Column(Integer, default=0)
    total_submissions = Column(Integer, default=0)

    submissions = relationship("Submission", back_populates="user")


class Problem(Base):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)  # e.g., CPP0101
    title = Column(String(200), nullable=False)
    category = Column(String(100), default="", index=True)  # Subject/category
    description = Column(Text, nullable=False)  # Markdown supported
    input_description = Column(Text, default="")
    output_description = Column(Text, default="")
    sample_input = Column(Text, default="")
    sample_output = Column(Text, default="")
    difficulty = Column(String(20), default=Difficulty.EASY)
    time_limit = Column(Float, default=1.0)  # seconds
    memory_limit = Column(Integer, default=256)  # MB
    created_at = Column(DateTime, default=datetime.utcnow)

    # Stats
    total_submissions = Column(Integer, default=0)
    accepted_count = Column(Integer, default=0)

    testcases = relationship("TestCase", back_populates="problem", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="problem")


class TestCase(Base):
    __tablename__ = "testcases"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False, index=True)
    input_data = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)
    is_sample = Column(Boolean, default=False)  # Shown to users
    order = Column(Integer, default=0)

    problem = relationship("Problem", back_populates="testcases")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False, index=True)
    language = Column(String(20), nullable=False)
    source_code = Column(Text, nullable=False)
    status = Column(String(30), default=SubmissionStatus.PENDING)
    score = Column(Float, default=0.0)  # 0-100
    time_ms = Column(Float, default=0.0)
    memory_kb = Column(Float, default=0.0)
    compile_error = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="submissions")
    problem = relationship("Problem", back_populates="submissions")
    results = relationship("SubmissionResult", back_populates="submission", cascade="all, delete-orphan")


class SubmissionResult(Base):
    __tablename__ = "submission_results"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)
    testcase_id = Column(Integer, ForeignKey("testcases.id"), nullable=False, index=True)
    status = Column(String(30), default=SubmissionStatus.PENDING)
    time_ms = Column(Float, default=0.0)
    memory_kb = Column(Float, default=0.0)
    actual_output = Column(Text, default="")

    submission = relationship("Submission", back_populates="results")
