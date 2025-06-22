
from sqlalchemy import Table, Column, Integer, String, Date, DateTime, Enum, ForeignKey, MetaData, Boolean
import enum
from datetime import datetime
metadata = MetaData()

#############################################################

# P_STATUS ENUM 정의
class ProjectStatus(enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ON_HOLD = "ON_HOLD"
    CANCELLED = "CANCELLED"

# 이슈 상태 ENUM 정의
class IssueStatus(enum.Enum):
    NOT_CHECKED = "NOT_CHECKED" # 미확인
    CHECKED = "CHECKED"         # 확인됨
    IN_PROGRESS = "IN_PROGRESS" # 진행 중
    COMPLETED = "COMPLETED"     # 완료
    ON_HOLD = "ON_HOLD"         # 보류 중

# 중요도 ENUM 정의
class PriorityEnum(enum.Enum):
    LOW = "LOW"         # 낮음
    MEDIUM = "MEDIUM"   # 보통
    HIGH = "HIGH"       # 높음

# 공개 여부 ENUM 정의
class ReleaseEnum(enum.Enum):
    PUBLIC = "PUBLIC"   # 공개
    PRIVATE = "PRIVATE" # 비공개

class AlertTypeEnum(enum.Enum):
    TEAM_INVITE = "TEAM_INVITE"  # 팀 초대
    ISSUE_NOTIFICATION = "ISSUE_NOTIFICATION"  # 이슈 알림
    ISSUE_DEADLINE_NEAR = "ISSUE_DEADLINE_NEAR"  # 이슈 마감 임박
    ISSUE_DEADLINE_OVER = "ISSUE_DEADLINE_OVER"  # 이슈 마감 초과


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
    Column("CREATE_DATE", Date)
)

# PROJECT 테이블
project = Table(
    "PROJECT",
    metadata,
    Column("P_ID", Integer, primary_key=True, autoincrement=True),
    Column("P_NAME", String(50), nullable=False),
    Column("P_CDATE", DateTime),
    Column("P_STATUS", Enum(ProjectStatus), default=ProjectStatus.IN_PROGRESS),
    Column("UID", String(30), ForeignKey("USER.UID")),
    Column("DISCRIPTION", String(200)),   # ✅ 추가
    Column("PRIORITY", String(20)),       # ✅ 추가
    Column("CATEGORY", String(50))        # ✅ 추가
)

# TEAM 테이블
team = Table(
    "TEAM",
    metadata,
    Column("T_ID", Integer, primary_key=True, autoincrement=True),
    Column("ROLE", String(30)),
    Column("U_ID", String(30), ForeignKey("USER.UID")),
    Column("P_ID", Integer, ForeignKey("PROJECT.P_ID")),
    Column("CREATE_DATE", Date)
)

# ISSUE 테이블
issue = Table(
    "ISSUE",
    metadata,
    Column("I_ID", Integer, primary_key=True, autoincrement=True),
    Column("TITLE", String(100), nullable=False),
    Column("CONTENT", String(300)),
    Column("I_STATUS", Enum(IssueStatus), default=IssueStatus.NOT_CHECKED),
    Column("I_RELEASE", Enum(ReleaseEnum), default=ReleaseEnum.PRIVATE),
    Column("PRIORITY", Enum(PriorityEnum), default=PriorityEnum.LOW),
    Column("CREATE_DATE", Date),
    Column("START_DATE", Date),
    Column("EXPIRE_DATE", Date),
    Column("FROM_UID", String(30), ForeignKey("USER.UID")),
    Column("FOR_UID", String(30), ForeignKey("USER.UID")),
    Column("P_ID", Integer, ForeignKey("PROJECT.P_ID"))
)

# ALERT 테이블
alert = Table(
    "ALERT",
    metadata,
    Column("A_ID", Integer, primary_key=True, autoincrement=True),
    Column("A_CATEGORY", Enum(AlertTypeEnum), nullable=False),
    Column("A_CONTENT", String(300), nullable=False),
    Column("A_READ", Boolean, default=False, nullable=False),
    Column("UID", String(30), ForeignKey("USER.UID")), # 수신자
    Column("P_ID", Integer, ForeignKey("PROJECT.P_ID"), nullable=True),
    Column("I_ID", Integer, ForeignKey("ISSUE.I_ID"), nullable=True)
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

# 🔹 Sprint Assign 테이블 정의
sprint_assign = Table(
    "SPRINT_ASSIGN",
    metadata,
    Column("ID", Integer, primary_key=True, autoincrement=True),
    Column("S_ID", Integer, ForeignKey("SPRINT.S_ID")),
    Column("UID", String(30), ForeignKey("USER.UID")),
    Column("ASSIGNED_DATE", Date)
)