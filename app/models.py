from datetime import datetime
from sqlalchemy import Table, Column, Integer, String, Date, DateTime, Enum, ForeignKey, MetaData
import enum

metadata = MetaData()

# P_STATUS ENUM 정의
class ProjectStatus(enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ON_HOLD = "ON_HOLD"
    CANCELLED = "CANCELLED"

class IssueStatus(enum.Enum):
    NOT_CHECKED = "NOT_CHECKED" # 미확인
    CHECKED = "CHECKED"         # 확인됨
    IN_PROGRESS = "IN_PROGRESS" # 진행 중
    COMPLETED = "COMPLETED"     # 완료
    ON_HOLD = "ON_HOLD"         # 보류 중

# 🔹 Sprint 상태 ENUM 정의
class SprintStatus(enum.Enum):
    TODO = "TODO"
    PROCESSING = "PROCESSING"
    REVIEW = "REVIEW"
    DONE = "DONE"

# USER 테이블
user = Table(
    "USER",
    metadata,
    Column("UID", String(30), primary_key=True),
    Column("NICKNAME", String(20), nullable=False),
    Column("PASSWORD", String(257), nullable=False),
    Column("EMAIL", String(50), nullable=False),
    Column("PHONE", String(11)),
    Column("CREATE_DATE", Date),
)

# PROJECT 테이블
project = Table(
    "PROJECT",
    metadata,
    Column("P_ID", Integer, primary_key=True, autoincrement=True),
    Column("P_NAME", String(50), nullable=False),
    Column("P_CDATE", DateTime),
    Column("P_STATUS", Enum(ProjectStatus), default=ProjectStatus.IN_PROGRESS),
    Column("UID", String(30), ForeignKey("USER.UID"))
)

# TEAM 테이블
team = Table(
    "TEAM",
    metadata,
    Column("T_ID", Integer, primary_key=True, autoincrement=True),
    Column("ROLE", String(30)),
    Column("U_ID", String(30), ForeignKey("USER.UID")),
    Column("P_ID", String(100), ForeignKey("PROJECT.P_ID")),
    Column("CREATE_DATE", Date),
)

# ISSUE 테이블
issue = Table(
    "ISSUE",
    metadata,
    Column("I_ID", Integer, primary_key=True, autoincrement=True),
    Column("TITLE", String(100), nullable=False),
    Column("CONTENT", String(300)),
    Column("I_STATE", String(20), default=IssueStatus.NOT_CHECKED),
    Column("I_RELEASE", String(20)),
    Column("PRIORITY", String(20)),
    Column("CREATE_DATE", Date),
    Column("START_DATE", Date),
    Column("EXPIRE_DATE", Date),
    Column("FROM_U_ID", String(30), ForeignKey("USER.UID")),
    Column("FOR_U_ID", String(30), ForeignKey("USER.UID")),
    Column("P_ID", String(100), ForeignKey("PROJECT.P_ID"))
)


# 🔹 Sprint 테이블 정의
sprint = Table(
    "SPRINT",
    metadata,
    Column("S_ID", Integer, primary_key=True, autoincrement=True),
    Column("TITLE", String(30)),
    Column("CONTENTS", String(30)),
    Column("P_ID", Integer, ForeignKey("PROJECT.P_ID")),  
    Column("STAT", Enum(SprintStatus)),
    Column("CREATE_DATE", Date)
)

# COMMENT 테이블 정의
comment = Table(
    "COMMENT",
    metadata,
    Column("C_ID", Integer, primary_key=True, autoincrement=True),
    Column("REF_TYPE", String(20), nullable=False),
    Column("REF_ID", Integer, nullable=False),
    Column("UID", String(30), ForeignKey("USER.UID"), nullable=False),
    Column("CONTENT", String(500), nullable=False),           # ✅ 변경된 부분
    Column("CREATE_DATE", DateTime, default=datetime.utcnow)
)
