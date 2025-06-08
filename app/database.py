import os
from dotenv import load_dotenv
from databases import Database
from sqlalchemy import create_engine, MetaData
import pymysql
pymysql.install_as_MySQLdb()

load_dotenv()

# MariaDB 연결 정보 설정

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")

DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# databases용 비동기 연결
database = Database(DATABASE_URL)

# sqlalchemy용 연결 (테이블 생성용)
engine = create_engine(DATABASE_URL.replace("+aiomysql", ""))

metadata = MetaData()
