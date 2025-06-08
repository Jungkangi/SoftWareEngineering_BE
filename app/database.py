import os
from dotenv import load_dotenv
from databases import Database
from sqlalchemy import create_engine, MetaData
import pymysql
import os

# pymysql을 MySQLdb처럼 사용하도록 설정 (sqlalchemy 호환 목적)
pymysql.install_as_MySQLdb()

load_dotenv()

# MariaDB 연결 정보 설정

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")

DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ✅ databases 라이브러리용 비동기 연결 객체
database = Database(DATABASE_URL)

# ✅ sqlalchemy 테이블 생성용 동기 연결 (aiomysql 제거)
engine = create_engine(DATABASE_URL.replace("+aiomysql", ""))

# ✅ 모든 테이블 메타데이터가 등록될 객체
metadata = MetaData()
