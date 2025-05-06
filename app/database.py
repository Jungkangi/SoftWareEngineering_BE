from databases import Database
from sqlalchemy import create_engine, MetaData
import pymysql
pymysql.install_as_MySQLdb()

# MariaDB 연결 정보 설정
DATABASE_URL = "mysql+aiomysql://root:1234@localhost:3306/shin"

# databases용 비동기 연결
database = Database(DATABASE_URL)

# sqlalchemy용 연결 (테이블 생성용)
engine = create_engine(DATABASE_URL.replace("+aiomysql", ""))

metadata = MetaData()

# test