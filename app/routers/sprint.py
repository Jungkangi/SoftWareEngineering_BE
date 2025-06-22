from fastapi import APIRouter, HTTPException, Depends, Path
from app.database import database
from app.models import sprint, SprintStatus, sprint_assign, user
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from app.dependencies import get_current_user
import sqlalchemy as sa

router = APIRouter()

# 🔹 요청용
class SprintCreate(BaseModel):
    TITLE: str
    CONTENTS: str
    P_ID: int
    STAT: Optional[SprintStatus] = SprintStatus.PROCESSING
    ASSIGNEES: Optional[List[str]] = None  # ✅ UID 리스트 추가

# 🔹 응답용
class SprintOut(SprintCreate):
    S_ID: int
    CREATE_DATE: Optional[date] = None

# 🔧 상태 수정용
class SprintUpdate(BaseModel):
    STAT: SprintStatus  # 필수 필드, 스프린트 상태만 수정 가능

class SprintAssignIn(BaseModel):
    S_ID: int
    UID: str

class SprintAssignOut(SprintAssignIn):
    ID: int
    ASSIGNED_DATE: date

class SprintAssignee(BaseModel):
    UID: str
    NICKNAME: str

class SprintWithAssigneesOut(SprintOut):
    ASSIGNEES: List[SprintAssignee]

# ✅ 특정 프로젝트의 모든 스프린트 조회 (권한 체크 X)
@router.get("/sprints/project/{projectid}", response_model=List[SprintWithAssigneesOut])
async def get_project_sprints(
    projectid: int,
    current_user: dict = Depends(get_current_user)
):
    # 1. 스프린트 조회
    sprint_query = sprint.select().where(sprint.c.P_ID == projectid)
    sprint_rows = await database.fetch_all(sprint_query)

    result = []

    for s in sprint_rows:
        # 2. 배정된 사용자 목록 조회 (JOIN user)
        assignee_query = sa.select(
            sprint_assign.c.UID,
            user.c.NICKNAME
        ).select_from(
            sprint_assign.join(user, sprint_assign.c.UID == user.c.UID)
        ).where(sprint_assign.c.S_ID == s["S_ID"])
        assignees = await database.fetch_all(assignee_query)

        # 3. 결과 조립
        result.append({
            **s,
            "ASSIGNEES": assignees
        })

    return result

# ✅ 스프린트 생성 API (JWT 인증 필요)
@router.post("/sprints/create", response_model=SprintOut)
async def create_sprint(
    data: SprintCreate,
    current_user: dict = Depends(get_current_user)
):
    # 1. 스프린트 생성
    sprint_data = {
        "TITLE": data.TITLE,
        "CONTENTS": data.CONTENTS,
        "P_ID": data.P_ID,
        "STAT": data.STAT
    }

    insert_query = sprint.insert().values(**sprint_data)
    new_sprint_id = await database.execute(insert_query)

    # 2. UID 리스트를 SPRINT_ASSIGN에 추가
    if data.ASSIGNEES:
        for uid in data.ASSIGNEES:
            assign_query = sprint_assign.insert().values(
                S_ID=new_sprint_id,
                UID=uid,
                ASSIGNED_DATE=date.today()
            )
            await database.execute(assign_query)

    # 3. 응답
    return {
        **sprint_data,
        "S_ID": new_sprint_id,
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
    current_user: dict = Depends(get_current_user)
):
    # 1. 해당 프로젝트의 스프린트 ID 목록 조회
    sprint_ids_query = sa.select(sprint.c.S_ID).where(sprint.c.P_ID == projectid)
    sprint_ids = await database.fetch_all(sprint_ids_query)

    # 2. 각 스프린트에 연결된 SPRINT_ASSIGN 삭제
    for s in sprint_ids:
        await database.execute(
            sprint_assign.delete().where(sprint_assign.c.S_ID == s["S_ID"])
        )

    # 3. 스프린트 삭제
    delete_sprint_query = sprint.delete().where(sprint.c.P_ID == projectid)
    await database.execute(delete_sprint_query)

    return {"message": f"프로젝트 ID {projectid}의 모든 스프린트 및 할당 정보가 삭제되었습니다."}

# ✅ 단일 스프린트 삭제
@router.delete("/sprints/{sprint_id}")
async def delete_single_sprint(
    sprint_id: int,
    current_user: dict = Depends(get_current_user)
):
    # 1. 스프린트 존재 확인
    existing = await database.fetch_one(sprint.select().where(sprint.c.S_ID == sprint_id))
    if not existing:
        raise HTTPException(status_code=404, detail="스프린트를 찾을 수 없습니다.")

    # 2. SPRINT_ASSIGN 먼저 삭제
    delete_assign_query = sprint_assign.delete().where(sprint_assign.c.S_ID == sprint_id)
    await database.execute(delete_assign_query)

    # 3. 스프린트 삭제
    delete_sprint_query = sprint.delete().where(sprint.c.S_ID == sprint_id)
    await database.execute(delete_sprint_query)

    return {"message": f"스프린트 ID {sprint_id} 및 관련 할당 정보가 삭제되었습니다."}

# ✅ 스프린트에 사용자 삭제 (POST 메서드, JWT 인증 필요)
@router.delete("/sprint-assign")
async def unassign_user_from_sprint(
    data: SprintAssignIn,
    current_user: dict = Depends(get_current_user)
):
    # 존재 여부 확인
    existing = await database.fetch_one(
        sprint_assign.select().where(
            (sprint_assign.c.S_ID == data.S_ID) &
            (sprint_assign.c.UID == data.UID)
        )
    )
    if not existing:
        raise HTTPException(status_code=404, detail="할당 정보가 없습니다.")

    # 삭제 실행
    delete_query = sprint_assign.delete().where(
        (sprint_assign.c.S_ID == data.S_ID) &
        (sprint_assign.c.UID == data.UID)
    )
    await database.execute(delete_query)

    return {"message": f"스프린트 {data.S_ID}에서 사용자 {data.UID}가 제거되었습니다."}

# ✅ 스프린트에 사용자 추가 (POST 메서드, JWT 인증 필요)
@router.post("/sprint-assign", response_model=SprintAssignOut)
async def assign_user_to_sprint(
    data: SprintAssignIn,
    current_user: dict = Depends(get_current_user)
):
    # 이미 할당돼 있으면 중복 방지
    exists = await database.fetch_one(
        sprint_assign.select().where(
            (sprint_assign.c.S_ID == data.S_ID) &
            (sprint_assign.c.UID == data.UID)
        )
    )
    if exists:
        raise HTTPException(status_code=400, detail="이미 해당 사용자에게 할당됨")

    # 새 할당 추가
    query = sprint_assign.insert().values(
        S_ID=data.S_ID,
        UID=data.UID,
        ASSIGNED_DATE=date.today()
    )
    new_id = await database.execute(query)

    result = await database.fetch_one(
        sprint_assign.select().where(sprint_assign.c.ID == new_id)
    )
    return result
