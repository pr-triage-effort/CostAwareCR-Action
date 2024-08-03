import os

from typing import List, Optional
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import ForeignKey, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker, DeclarativeBase, Session, relationship

CACHE_RESET = os.environ.get("RESET_CACHE")

db = sa.create_engine('sqlite:///hist_cache.db', echo=False)
Session = sessionmaker(bind=db)

def init_db() -> None:
    if CACHE_RESET == 'true':
        print('Cached db entries will be reset')
        if os.path.isfile('./hist_cache.db'):
            os.remove('./hist_cache.db')

    Base.metadata.create_all(db)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(unique=True)
    tag: Mapped[str]
    type: Mapped[str] = mapped_column (nullable=True)
    experience: Mapped[float] = mapped_column(nullable=True)
    total_change_number: Mapped[int] = mapped_column(nullable=True)
    review_number: Mapped[int] = mapped_column(nullable=True)
    changes_per_week: Mapped[float] = mapped_column(nullable=True)
    global_merge_ratio: Mapped[float] = mapped_column(nullable=True)
    project_merge_ratio: Mapped[float] = mapped_column(nullable=True)

    def __status__(self) -> str:
        return f"<User(username={self.username}, tag={self.tag}, type={self.type})>"

class Project(Base):
    __tablename__ = 'projects'

    name: Mapped[str] = mapped_column(primary_key=True, unique=True)
    changes_per_week: Mapped[float] = mapped_column(nullable=True)
    changes_per_author: Mapped[float] = mapped_column(nullable=True)
    merge_ratio: Mapped[float] = mapped_column(nullable=True)
    last_update: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    def __status__(self) -> str:
        return f"<Project(name={self.name}, cpw={self.changes_per_week}, cpa={self.changes_per_author}, mr={self.merge_ratio})>"

class PrReviewers(Base):
    __tablename__ = 'pr_reviewers'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    humans: Mapped[int]
    bots: Mapped[int]
    avg_experience: Mapped[float]
    avg_reviews: Mapped[float]

    pr_num: Mapped[int] = mapped_column(ForeignKey('pull_requests.number'))
    pr: Mapped['PullRequest'] = relationship(back_populates='reviewer_feat')

    def __status__(self) -> str:
        return f"<PrReviewers(pr={self.pr_num}, humans={self.humans}, bots={self.bots}, avg_exp={self.avg_experience}, avg_reviews={self.avg_reviews})>"
    
class PrText(Base):
    __tablename__ = 'pr_text'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    description_len: Mapped[int]
    is_documentation: Mapped[int] = mapped_column(CheckConstraint('is_documentation IN (0, 1)'), default=0)
    is_bug_fixing: Mapped[int] = mapped_column(CheckConstraint('is_bug_fixing IN (0, 1)'), default=0)
    is_feature: Mapped[int] = mapped_column(CheckConstraint('is_feature IN (0, 1)'), default=0)

    pr_num: Mapped[int] = mapped_column(ForeignKey('pull_requests.number'))
    pr: Mapped['PullRequest'] = relationship(back_populates='text_feat')

    def __status__(self) -> str:
        return f"<PrText(pr={self.pr_num}, desc_len={self.description_len}, doc={self.is_documentation}, fix={self.is_bug_fixing}, feat={self.is_feature})>"
    
class PrCode(Base):
    __tablename__ = 'pr_code'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    num_of_directory: Mapped[int]
    modify_entropy: Mapped[float]
    lines_added: Mapped[int]
    lines_deleted: Mapped[int]
    files_added: Mapped[int]
    files_deleted: Mapped[int]
    files_modified: Mapped[int]
    subsystem_num: Mapped[int]

    pr_num: Mapped[int] = mapped_column(ForeignKey('pull_requests.number'))
    pr: Mapped['PullRequest'] = relationship(back_populates='code_feat')

    def __status__(self) -> str:
        return f"<PrCode(pr={self.pr_num}, num_dir={self.num_of_directory}, mod_entropy={self.modify_entropy}, l_add={self.lines_added}, l_del={self.lines_deleted}, f_add={self.files_added}, f_del={self.files_deleted}, f_mod={self.files_modified}, num_subsys={self.subsystem_num})>"

class PullRequest(Base):
    __tablename__ = 'pull_requests'

    number: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    merged: Mapped[bool]
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=True)

    author: Mapped[User | None] = relationship("User")
    reviewer_feat: Mapped[PrReviewers | None] = relationship(back_populates='pr')
    text_feat: Mapped[PrText | None] = relationship(back_populates='pr')
    code_feat: Mapped[PrCode | None] = relationship(back_populates='pr')

    def __status__(self) -> str:
        return f"<PR(pr={self.number}, title={self.title}, author={self.author}, rev_ft={self.reviewer_feat}, text_ft={self.text_feat}, code_ft={self.code_feat})>"


def db_get_user(username: str, session: Session) -> User:
    return session.get(User, {'username': username})

def db_get_project(name: str, session: Session) -> Project:
    return session.get(Project, {'name': name})
