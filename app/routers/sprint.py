from fastapi import APIRouter, HTTPException, Depends, Path
from app.database import database
from app.models import sprint, SprintStatus
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from app.dependencies import get_current_user

router = APIRouter()

# 🔹 요청용
class SprintCreate(BaseModel):
    TITLE: str
    CONTENTS: str
    P_ID: int
    STAT: Optional[SprintStatus] = SprintStatus.PROCESSING  # 기본값: PROCESSING

# 🔹 응답용
class SprintOut(SprintCreate):
    S_ID: int
    CREATE_DATE: Optional[date] = None

# 🔧 상태 수정용
class SprintUpdate(BaseModel):
    STAT: SprintStatus  # 필수 필드, 스프린트 상태만 수정 가능

# ✅ 특정 프로젝트의 모든 스프린트 조회 (권한 체크 X)
@router.get("/sprints/project/{projectid}", response_model=List[SprintOut])
async def get_project_sprints(
    projectid: int,
    current_user: dict = Depends(get_current_user)  # 🔐 JWT 인증 추가
):
    """
    특정 프로젝트에 속한 모든 스프린트 목록을 반환합니다.
    로그인한 사용자만 조회할 수 있습니다.
    """
    query = sprint.select().where(sprint.c.P_ID == projectid)
    return await database.fetch_all(query)

# ✅ 스프린트 생성 API (JWT 인증 필요)
@router.post("/sprints/create", response_model=SprintOut)
async def create_sprint(
    data: SprintCreate,
    current_user: dict = Depends(get_current_user)  # 🔐 JWT 기반 사용자 인증
):
    """
    로그인한 사용자만 스프린트를 생성할 수 있습니다.
    STAT 값을 입력하지 않으면 기본값 PROCESSING으로 설정됩니다.
    """
    query = sprint.insert().values(**data.dict())
    new_id = await database.execute(query)
    
    return {
        **data.dict(),
        "S_ID": new_id,
        "CREATE_DATE": date.today()
    }

# ✅ 스프린트 상태 수정 API (PUT 메서드, JWT 인증 필요)
@router.put("/sprints/{sprint_id}", response_model=SprintOut)
async def update_sprint_stat(
    sprint_id: int = Path(..., description="수정할 스프린트 ID"),
    data: SprintUpdate = ...,  # 요청 본문에서 STAT 값 받음
    current_user: dict = Depends(get_current_user)  # 🔐 JWT 기반 사용자 인증
):
    """
    특정 스프린트의 상태(STAT)를 수정합니다.
    로그인된 사용자만 요청할 수 있습니다.
    """
    # 1. 스프린트 존재 여부 확인
    existing = await database.fetch_one(sprint.select().where(sprint.c.S_ID == sprint_id))
    if not existing:
        raise HTTPException(status_code=404, detail="해당 스프린트를 찾을 수 없습니다.")

    # 2. 상태 업데이트 실행
    update_query = sprint.update().where(sprint.c.S_ID == sprint_id).values(STAT=data.STAT)
    await database.execute(update_query)

    # 3. 변경된 결과 다시 조회 후 반환
    updated = await database.fetch_one(sprint.select().where(sprint.c.S_ID == sprint_id))
    return updated

# ✅ 특정 프로젝트의 모든 스프린트 삭제
@router.delete("/sprints/project/{projectid}")
async def delete_sprints_by_project(
    projectid: int,
    current_user: dict = Depends(get_current_user)  # 🔐 JWT 인증
):
    """
    특정 프로젝트에 연결된 모든 스프린트를 삭제합니다.
    로그인한 사용자만 요청할 수 있습니다.
    """
    delete_query = sprint.delete().where(sprint.c.P_ID == projectid)
    result = await database.execute(delete_query)
    return {"message": f"프로젝트 ID {projectid}에 속한 스프린트가 삭제되었습니다."}

# ✅ 단일 스프린트 삭제
@router.delete("/sprints/{sprint_id}")
async def delete_single_sprint(
    sprint_id: int,
    current_user: dict = Depends(get_current_user)  # 🔐 JWT 인증
):
    """
    특정 스프린트 하나만 삭제합니다.
    로그인한 사용자만 요청할 수 있습니다.
    """
    # 1. 존재 여부 확인
    existing = await database.fetch_one(sprint.select().where(sprint.c.S_ID == sprint_id))
    if not existing:
        raise HTTPException(status_code=404, detail="스프린트를 찾을 수 없습니다.")

    # 2. 삭제 실행
    delete_query = sprint.delete().where(sprint.c.S_ID == sprint_id)
    await database.execute(delete_query)

    return {"message": f"스프린트 ID {sprint_id}가 삭제되었습니다."}