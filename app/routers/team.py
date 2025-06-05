from fastapi import APIRouter, Depends, HTTPException
from app.database import database
from app.models import team, user, project
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from app.dependencies import get_current_user
import sqlalchemy as sa

router = APIRouter()

# 🔹 요청 스키마: 팀 생성 및 팀원 추가 시 사용되는 형식
class TeamIn(BaseModel):
    ROLE: Optional[str] = None
    P_NAME: str  # 🔄 P_ID 대신 프로젝트 이름 사용
    CREATE_DATE: Optional[date] = None

# 🔹 팀원 추가 요청 스키마: 팀에 새로운 멤버를 추가할 때 사용되는 형식
class AddMemberIn(BaseModel):
    U_ID: str
    ROLE: Optional[str] = None
    P_NAME: str
    CREATE_DATE: Optional[date] = None


# ✅ 응답 스키마: 팀 정보를 반환할 때 사용되는 형식
class TeamOut(BaseModel):
    T_ID: int
    U_ID: str
    P_ID: int
    ROLE: Optional[str] = None
    CREATE_DATE: Optional[date] = None

# ✅ 팀 생성 API: 현재 사용자를 PM으로 등록 (인증 필요)
@router.post("/teams/create", response_model=TeamOut)
async def create_team_as_pm(
    team_data: TeamIn,
    current_user: dict = Depends(get_current_user)
):
    # 프로젝트 이름으로 P_ID 조회
    project_query = sa.select(project.c.P_ID).where(project.c.P_NAME == team_data.P_NAME)
    project_row = await database.fetch_one(project_query)

    if not project_row:
        raise HTTPException(status_code=404, detail="해당 프로젝트 이름이 존재하지 않습니다.")
    
    values = {
        "ROLE": team_data.ROLE or "PM",
        "P_ID": project_row.P_ID,
        "U_ID": current_user["UID"],
        "CREATE_DATE": team_data.CREATE_DATE or date.today()
    }

    insert_query = team.insert().values(**values)
    last_id = await database.execute(insert_query)

    return {**values, "T_ID": last_id}

# ✅ 팀원 추가 API: PM이 다른 팀원을 추가 (인증 필요)
@router.post("/teams/add", response_model=TeamOut)
async def add_team_member_by_pm(
    team_data: AddMemberIn,
    current_user: dict = Depends(get_current_user)
):
    # 1. 프로젝트 이름 → P_ID 매핑
    project_query = sa.select(project.c.P_ID).where(project.c.P_NAME == team_data.P_NAME)
    project_row = await database.fetch_one(project_query)

    if not project_row:
        raise HTTPException(status_code=404, detail="해당 프로젝트 이름이 존재하지 않습니다.")

    p_id = project_row.P_ID

    # 2. 현재 사용자가 이 프로젝트의 PM인지 확인
    check_pm_query = sa.select(team).where(
        team.c.P_ID == p_id,
        team.c.U_ID == current_user["UID"],
        team.c.ROLE == "PM"
    )
    pm_exists = await database.fetch_one(check_pm_query)
    if not pm_exists:
        raise HTTPException(status_code=403, detail="PM 권한이 필요합니다.")

    # 3. 팀원 추가
    values = {
        "ROLE": team_data.ROLE,
        "P_ID": p_id,
        "U_ID": team_data.U_ID,
        "CREATE_DATE": team_data.CREATE_DATE or date.today()
    }

    insert_query = team.insert().values(**values)
    last_id = await database.execute(insert_query)

    return {**values, "T_ID": last_id}


# ✅ 전체 팀원 조회 (인증 필요 없음: 공개 정보면 허용)
@router.get("/teams/", response_model=List[TeamOut])
async def get_teams():
    query = team.select()
    return await database.fetch_all(query)

@router.get("/teams/my", response_model=List[TeamOut])
async def get_my_teams(current_user: dict = Depends(get_current_user)):
    """
    로그인한 사용자가 속한 팀 목록을 조회합니다.
    JWT에서 UID를 추출하여 해당 사용자의 팀만 반환합니다.
    """
    uid = current_user["UID"]
    query = team.select().where(team.c.U_ID == uid)
    return await database.fetch_all(query)

# ✅ 팀 검색 API: 닉네임 또는 프로젝트 이름 기반 검색 (내부 사용자 인증 필요)
@router.get("/teams/search", response_model=List[TeamOut])
async def search_teams(
    nickname: Optional[str] = None,
    project_name: Optional[str] = None,
    current_user: dict = Depends(get_current_user)  # JWT 검증용
):
    # 팀, 사용자, 프로젝트 테이블을 조인
    query = sa.select(team).select_from(
        team.join(user, team.c.U_ID == user.c.UID)
            .join(project, team.c.P_ID == project.c.P_ID)
    )

    # 검색 조건: 닉네임
    if nickname:
        query = query.where(user.c.NICKNAME == nickname)

    # 검색 조건: 프로젝트 이름
    if project_name:
        query = query.where(project.c.P_NAME == project_name)

    return await database.fetch_all(query)