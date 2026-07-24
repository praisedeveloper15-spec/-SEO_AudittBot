from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, BigInteger, DateTime, ForeignKey, Text, JSON, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    domain = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    owner = relationship("User", back_populates="projects")
    keywords = relationship("Keyword", back_populates="project", cascade="all, delete-orphan")
    audits = relationship("AuditReport", back_populates="project", cascade="all, delete-orphan")


class Keyword(Base):
    __tablename__ = "keywords"
    __table_args__ = (
        UniqueConstraint("project_id", "term", "engine", "device", "location_code",
                          name="uq_keyword_target"),
    )

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    term = Column(String(500), nullable=False)
    engine = Column(String(20), default="google")   # google | bing | yahoo | youtube
    device = Column(String(10), default="desktop")   # desktop | mobile
    location_code = Column(Integer, default=2840)     # DataForSEO location code, default = USA
    language_code = Column(String(10), default="en")
    active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    project = relationship("Project", back_populates="keywords")
    snapshots = relationship("RankSnapshot", back_populates="keyword", cascade="all, delete-orphan")


class RankSnapshot(Base):
    __tablename__ = "rank_snapshots"

    id = Column(Integer, primary_key=True)
    keyword_id = Column(Integer, ForeignKey("keywords.id"), nullable=False)
    position = Column(Integer, nullable=True)  # NULL = not found in top results
    url = Column(Text, nullable=True)
    checked_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    keyword = relationship("Keyword", back_populates="snapshots")


class AuditReport(Base):
    __tablename__ = "audit_reports"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    url = Column(Text, nullable=False)
    issues = Column(JSON, nullable=True)   # list of {severity, message}
    metrics = Column(JSON, nullable=True)  # title, meta_desc, word_count, h1_count, etc.
    created_at = Column(DateTime(timezone=True), default=utcnow)

    project = relationship("Project", back_populates="audits")
