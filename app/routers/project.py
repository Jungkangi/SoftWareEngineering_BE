from enum import Enum
from fastapi import APIRouter, HTTPException, Depends
from app.database import database
from app.models import project, user, team
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
    DISCRIPTION: Optional[str] = None
    PRIORITY: Optional[str] = None
    CATEGORY: Optional[str] = None
    # UID는 더 이상 클라이언트로부터 받지 않음 → JWT로 추출

# ✅ 응답용 스키마: API가 반환할 프로젝트 데이터 형식
class ProjectOut(ProjectIn):
    P_ID: int
    P_CDATE: datetime | None = None  # 프로젝트 생성일 (응답 전용 필드)


class UserInProject(BaseModel):
    UID: str
    NICKNAME: str

# ✅ 프로젝트와 사용자 정보를 함께 반환하기 위한 스키마
class ProjectWithUsersOut(ProjectOut):
    P_ID: int
    USERS: List[UserInProject]

# ✅ 프로젝트 업데이트 요청용 스키마
class ProjectUpdate(BaseModel):
    P_NAME: Optional[str] = None
    DISCRIPTION: Optional[str] = None
    PRIORITY: Optional[str] = None
    CATEGORY: Optional[str] = None

# ✅ 전체 프로젝트 조회 (모든 사용자용 - 공개 프로젝트라면)
@router.get("/projects/", response_model=List[ProjectOut])
async def get_projects():
    query = project.select()
    return await database.fetch_all(query)

# ✅ 프로젝트 생성 (인증된 사용자만 가능)
@router.post("/projects/", response_model=ProjectOut)
async def create_project(
    data: ProjectIn,
    current_user: dict = Depends(get_current_user)
):
    values = data.dict()
    values["UID"] = current_user["UID"]
    values["P_CDATE"] = datetime.utcnow()  # ✅ 실제 생성 시간 기록

    # 프로젝트 INSERT
    insert_query = project.insert().values(**values)
    new_project_id = await database.execute(insert_query)

    # ✅ 생성된 정보 반환
    return {
        "P_ID": new_project_id,
        **data.dict(),
        "P_CDATE": values["P_CDATE"]
    }

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

# ✅ 내 프로젝트와 참여 중인 사용자 정보 조회
@router.get("/projects/my/with-users", response_model=List[ProjectWithUsersOut])
async def get_my_projects_with_users(current_user: dict = Depends(get_current_user)):
    uid = current_user["UID"]

    # 1. 사용자가 생성한 프로젝트 조회
    project_query = sa.select(project).where(project.c.UID == uid)
    projects = await database.fetch_all(project_query)

    result = []

    for p in projects:
        # 2. 프로젝트 ID 기준으로 참여 중인 사용자 조회
        user_query = sa.select(user.c.UID, user.c.NICKNAME).select_from(
            team.join(user, team.c.U_ID == user.c.UID)
        ).where(team.c.P_ID == p["P_ID"])
        user_list = await database.fetch_all(user_query)

        result.append({
            "P_ID": p["P_ID"],
            "P_NAME": p["P_NAME"],
            "P_STATUS": p["P_STATUS"],
            "P_CDATE": p["P_CDATE"],
            "DISCRIPTION": p["DISCRIPTION"],  # ✅ 추가
            "PRIORITY": p["PRIORITY"],        # ✅ 추가
            "CATEGORY": p["CATEGORY"],        # ✅ 추가
            "USERS": user_list
        })

    return result

# ✅ 프로젝트 수정 (PM만 가능)
@router.put("/projects/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    current_user: dict = Depends(get_current_user)
):
    uid = current_user["UID"]

    # ✅ 이 사용자가 PM인지 확인
    pm_check_query = sa.select(team).where(
        team.c.P_ID == project_id,
        team.c.U_ID == uid,
        team.c.ROLE == "PM"
    )
    is_pm = await database.fetch_one(pm_check_query)
    if not is_pm:
        raise HTTPException(status_code=403, detail="이 프로젝트의 PM만 수정할 수 있습니다.")

    # ✅ 프로젝트 존재 확인
    project_query = project.select().where(project.c.P_ID == project_id)
    existing_project = await database.fetch_one(project_query)
    if not existing_project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")

    # ✅ 수정할 값 준비
    update_values = {k: v for k, v in data.dict().items() if v is not None}

    # ✅ 업데이트 수행
    update_query = project.update().where(project.c.P_ID == project_id).values(**update_values)
    await database.execute(update_query)

    # ✅ 수정 후 결과 반환
    updated_project = await database.fetch_one(project.select().where(project.c.P_ID == project_id))
    return updated_project

# ✅ 프로젝트 삭제 (PM만 가능)
@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    current_user: dict = Depends(get_current_user)
):
    uid = current_user["UID"]

    # ✅ PM 여부 확인
    pm_check_query = sa.select(team).where(
        team.c.P_ID == project_id,
        team.c.U_ID == uid,
        team.c.ROLE == "PM"
    )
    is_pm = await database.fetch_one(pm_check_query)

    if not is_pm:
        raise HTTPException(status_code=403, detail="PM만 프로젝트를 삭제할 수 있습니다.")

    # ✅ 프로젝트 존재 여부 확인
    project_check_query = project.select().where(project.c.P_ID == project_id)
    project_row = await database.fetch_one(project_check_query)

    if not project_row:
        raise HTTPException(status_code=404, detail="해당 프로젝트가 존재하지 않습니다.")

    # ✅ 팀 삭제 (P_ID 기준)
    delete_teams_query = team.delete().where(team.c.P_ID == project_id)
    await database.execute(delete_teams_query)

    # ✅ 프로젝트 삭제
    delete_project_query = project.delete().where(project.c.P_ID == project_id)
    await database.execute(delete_project_query)

    return {"message": f"프로젝트 ID {project_id} 및 관련 팀이 삭제되었습니다."}
