from enum import Enum
from fastapi import APIRouter, HTTPException, Depends
from app.database import database
from app.models import project, user
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import sqlalchemy as sa
from datetime import date
from app.dependencies import get_current_user

router = APIRouter()

class P_Enum(str, Enum):
    IN_PROGRESS = "IN_PROGRESS" # 진행 중
    COMPLETED = "COMPLETED"     # 완료
    ON_HOLD = "ON_HOLD"         # 보류 중
    CANCELLED = "CANCELLED"     # 취소됨

# ✅ 요청용 스키마: 클라이언트가 보낼 데이터 형식 정의
class ProjectIn(BaseModel):
    P_NAME: str                    # 프로젝트 이름
    P_STATUS: P_Enum = Field(description= "상태", default=P_Enum.IN_PROGRESS)
    # UID는 더 이상 클라이언트로부터 받지 않음 → JWT로 추출

# ✅ 응답용 스키마: API가 반환할 프로젝트 데이터 형식
class ProjectOut(ProjectIn):
    P_CDATE: datetime | None = None  # 프로젝트 생성일 (응답 전용 필드)

# ✅ 전체 프로젝트 조회 (모든 사용자용 - 공개 프로젝트라면)
@router.get("/projects/", response_model=List[ProjectOut])
async def get_projects():
    query = project.select()
    return await database.fetch_all(query)

# ✅ 프로젝트 생성 (인증된 사용자만 가능)
@router.post("/projects/", response_model=ProjectOut)
async def create_project(
    data: ProjectIn,
    current_user: dict = Depends(get_current_user)  # JWT에서 UID 추출
):
    # 현재 로그인한 사용자의 UID로 프로젝트 작성자 설정
    values = data.dict()
    values["UID"] = current_user["UID"]

    query = project.insert().values(**values)
    await database.execute(query)
    return values

# ✅ 내 프로젝트 조회
@router.get("/projects/my", response_model=List[ProjectOut])
async def get_my_projects(current_user: dict = Depends(get_current_user)):
    """
    로그인한 사용자가 생성한 프로젝트 목록을 조회합니다.
    JWT에서 UID를 추출하여 해당 사용자의 프로젝트만 반환합니다.
    """
    uid = current_user["UID"]
    query = project.select().where(project.c.UID == uid)
    return await database.fetch_all(query)
