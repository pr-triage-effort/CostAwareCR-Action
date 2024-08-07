import os
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker, DeclarativeBase, Session

db = sa.create_engine('sqlite:///cache.db', echo=False)
Session = sessionmaker(bind=db)

def init_db(reset: bool) -> None:
    if reset:
        print('Cached db entries will be reset')
        if os.path.isfile('./cache.db'):
            os.remove('./cache.db')

    Base.metadata.create_all(db)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'

    username: Mapped[str] = mapped_column(primary_key=True, unique=True)
    tag: Mapped[str]
    type: Mapped[str] = mapped_column(nullable=True)
    experience: Mapped[float]
    total_change_number: Mapped[int] = mapped_column(nullable=True)
    review_number: Mapped[int]
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

    def __status__(self) -> str:
        return f"<Project(name={self.name}, cpw={self.changes_per_week}, cpa={self.changes_per_author}, mr={self.merge_ratio})>"


def db_get_user(username: str, session: Session) -> User:
    return session.get(User, {'username': username})

def db_get_project(name: str, session: Session) -> Project:
    return session.get(Project, {'name': name})
