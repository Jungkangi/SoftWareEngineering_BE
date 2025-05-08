from fastapi import APIRouter, HTTPException, Depends, status
from app.database import database
from app.models import project, user
from pydantic import BaseModel, validator, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import sqlalchemy as sa
from datetime import date
from app.dependencies import get_current_user

from enum import Enum
from ..models import issue, project, user
from sqlalchemy import and_, or_

router = APIRouter()


# read_project_member() 함수에서 사용할 USER 테이블의 UID와 NICKNAME을 포함하는 스키마
class UserSelect(BaseModel):
    UID: str
    NICKNAME: str
    class Config:
        from_attributes = True # Pydantic v2.x에서 사용되는 설정

class ReleaseEnum(str, Enum):
    PUBLIC = "PUBLIC"   # 공개
    PRIVATE = "PRIVATE" # 비공개

class PriorityEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class StateEnum(str, Enum):
    NOT_CHECKED = "NOT_CHECKED" # 미확인
    CHECKED = "CHECKED"         # 확인됨
    IN_PROGRESS = "IN_PROGRESS" # 진행 중
    COMPLETED = "COMPLETED"     # 완료
    ON_HOLD = "ON_HOLD"         # 보류 중


# ✅ 요청용 스키마: 클라이언트가 보낼 데이터 형식 정의
class ISSUE_Create(BaseModel):
    TITLE: str      # 이슈 제목
    CONTENT: str    # 이슈 내용
    PRIORITY: PriorityEnum = Field(description= "중요도", default=PriorityEnum.MEDIUM)
    I_STATE: StateEnum = Field(description = "상태", default=StateEnum.NOT_CHECKED)
    I_RELEASE: ReleaseEnum = Field(description= "공개 여부", default=ReleaseEnum.PRIVATE)
    FOR_U_ID: str  # 이슈 수신자 (UID)
    P_ID: str
    START_DATE: date | None = None
    EXPIRE_DATE: date | None = None

# ✅ 응답용 스키마: API가 반환할 프로젝트 데이터 형식
class ISSUEOut(ISSUE_Create):
    I_CDATE: datetime | None = None  # 프로젝트 생성일 (응답 전용 필드)


###########################################################################

# ✅ 전체 이슈 조회 (선택된 프로젝트 내의 모든 이슈 / 해당 프로젝트 관련자만 가능)
@router.get("/issues/{project_id}", response_model=List[ISSUEOut])
async def get_issues(project_id: str, current_user: dict = Depends(get_current_user)):

    """
    주어진 프로젝트 ID에 해당하는 모든 이슈를 조회합니다.
        - public 이슈 - 모든 사용자가 조회 가능
        - private 이슈 - 현재 사용자가 작성자 이거나 수신자일 때만 조회 가능
    """

    query = sa.select(
        issue.c.TITLE,
        issue.c.CONTENT,
        issue.c.I_STATE,
        issue.c.PRIORITY,
        issue.c.I_RELEASE,
        issue.c.START_DATE,
        issue.c.EXPIRE_DATE,
        issue.c.FROM_U_ID,
        issue.c.FOR_U_ID
    ).where(
        and_(
            issue.c.P_ID == project_id,
            or_(
                issue.c.I_RELEASE == ReleaseEnum.PUBLIC,
                and_(
                    issue.c.I_RELEASE == ReleaseEnum.PRIVATE,
                    or_(
                        issue.c.FOR_U_ID == current_user["UID"],
                        issue.c.FROM_U_ID == current_user["UID"]
                    )
                )
            )
        )
    ) .order_by(issue.c.CREATE_DATE.desc())

    db_issue = await database.fetch_all(query)

    if not db_issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    return db_issue

# ✅ 특정 이슈 상세 조회 (이슈 ID로 조회)
@router.get("/issues/{issue_id}", response_model=ISSUEOut)
async def view_issue(issue_id: int, current_user: dict = Depends(get_current_user)):

    """
    사용자가 선택한 이슈 ID에 해당하는 이슈를 조회합니다.
    이슈의 상세한 정보를 확인할 수 있습니다.
    """

    query = sa.select(
        issue.c.TITLE,
        issue.c.CONTENT,
        issue.c.I_STATE,
        issue.c.PRIORITY,
        issue.c.I_RELEASE,
        issue.c.START_DATE,
        issue.c.EXPIRE_DATE,
        issue.c.FROM_U_ID,
        issue.c.FOR_U_ID
    ).where(
        and_(
            issue.c.I_ID == issue_id,
            or_(
                issue.c.I_RELEASE == ReleaseEnum.PUBLIC,
                and_(
                    issue.c.I_RELEASE == ReleaseEnum.PRIVATE,
                    or_(
                        issue.c.FOR_U_ID == current_user["UID"],
                        issue.c.FROM_U_ID == current_user["UID"]
                    )
                )
            )
        )
    )

    db_issue = await database.fetch_one(query)

    if not db_issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    return db_issue

# ✅ 이슈 생성 ( 인증된 사용자만 가능 )
@router.post("/issues/", response_model=ISSUEOut)
async def create_issue(data: ISSUE_Create, current_user: dict = Depends(get_current_user)):

    """
    새로운 이슈를 생성합니다.
    이슈는 특정 프로젝트에 속합니다.
       - 이슈 작성자는 현재 로그인한 사용자로 설정됩니다.
       - 이슈 수신자는 클라이언트에서 전달받은 for_U_ID로 설정됩니다.
       - 
    """

    values = data

    # 현재 로그인한 사용자의 UID로 이슈 작성자 설정
    values["FROM_U_ID"] = current_user["UID"]

    query = issue.insert().values(**values)
    await database.execute(query)
    return values


# ✅ 이슈 수정 ( 이슈를 생성하거나 받은 사용자만 가능 )
@router.post("/issues/{issue_id}", response_model=ISSUEOut)
async def update_issue(issue_id: int, data: ISSUE_Create, current_user: dict = Depends(get_current_user)):

    """
    주어진 이슈 ID에 해당하는 이슈를 수정합니다.
    이슈는 특정 프로젝트에 속합니다.
       - 이슈 제목
       - 이슈 내용
       - 이슈 상태
       - 이슈 중요도
       - 이슈 공개 여부
       - 이슈 만료일
    """

    query = issue.select().where(
        and_(
            issue.c.I_ID == issue_id
            or_(
                issue.c.ReleaseEnum == ReleaseEnum.PUBLIC,
                issue.c.FOR_U_ID == current_user["UID"],
                issue.c.FROM_U_ID == current_user["UID"]
            ))
        )
    db_issue = await database.fetch_one(query)

    if not db_issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    
    if not (db_issue["FROM_U_ID"] == current_user["UID"] or db_issue["FOR_U_ID"] == current_user["UID"]):
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this issue"
        )

    query = issue.update(
        issue.c.TITLE,
        issue.c.CONTENT,
        issue.c.I_STATE,
        issue.c.PRIORITY,
        issue.c.I_RELEASE,
        issue.c.START_DATE,
        issue.c.EXPIRE_DATE,
        issue.c.FROM_U_ID,
        issue.c.FOR_U_ID
    ).where(
        and_(
            issue.c.P_ID == data.P_ID,
            or_(
                issue.c.FOR_U_ID == current_user["UID"],
                issue.c.FROM_U_ID == current_user["UID"]
        ))
    )
    
    await database.execute(query)
    return values
