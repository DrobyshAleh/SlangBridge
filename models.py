# models.py
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, ForeignKey, Text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)  # можно False
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(2), default="ru")
    level: Mapped[str] = mapped_column(String(5), default="A1")


class ForumPost(Base):
    __tablename__ = "forum_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    images: Mapped[str] = mapped_column(Text, default="")  # JSON или CSV строка
    approved: Mapped[bool] = mapped_column(default=False)


class Ad(Base):
    __tablename__ = "ads"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    category: Mapped[str] = mapped_column(String(50))
    text: Mapped[str] = mapped_column(Text)


class Phrase(Base):
    __tablename__ = "phrases"

    id: Mapped[int] = mapped_column(primary_key=True)
    phrase: Mapped[str] = mapped_column(String(255))
    translation: Mapped[str] = mapped_column(String(255))


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(5))
    content: Mapped[str] = mapped_column(Text)  # можно как JSON-строка
