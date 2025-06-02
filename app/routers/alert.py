

"""
ALERT

- 프로젝트 = 팀초대 받으면 ALERT
- 프로젝트 = 이슈 받으면 ALERT
    - 이슈 상태 변화에 따른 ALERT 할지 말지
- 프로젝트 = 프로젝트 마감 기한이 다가오면 ALERT
- 프로젝트 = 프로젝트 마감되었으면 ALERT

"""

################################################################################


from fastapi import APIRouter, HTTPException, Depends, status
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional
import sqlalchemy as sa

from app.database import database
from app.dependencies import get_current_user
from app.models import alert
from app.models import AlertCategory

router = APIRouter()


# read_project_member() 함수에서 사용할 USER 테이블의 UID와 NICKNAME을 포함하는 스키마
class AlertCreate(BaseModel):
    A_CATEGORY: AlertCategory
    A_CONTENT: str
    UID: str
    PID: Optional[int] = None  # 프로젝트 ID (선택적)
    I_ID: Optional[int] = None  # 이슈 ID (선택적)

# ✅ 요청용 스키마: 클라이언트가 보낼 데이터 형식 정의
class AlertOut(BaseModel):
    A_ID: int
    A_CATEGORY: AlertCategory
    A_CONTENT: str
    A_READ: bool = Field(default=False, description="알림 읽음 여부")
    UID: str  # 수신자 UID
    P_ID: Optional[int] = None  # 프로젝트 ID (선택적)
    I_ID: Optional[int] = None  # 이슈 ID (선택적)


###########################################################################

# ✅ 알림 생성 - 
@router.get("/alerts/create", response_model=List[AlertOut])
async def create_alert(data: AlertCreate, current_user: dict = Depends(get_current_user)):

    """
    새로운 알림을 생성합니다.
    알림은 특정 프로젝트 또는 이슈에 관련된 정보를 포함합니다.
       - 알림 작성자는 현재 로그인한 사용자로 설정됩니다.
       - 알림 수신자는 클라이언트에서 전달받은 UID로 설정됩니다.
       - 프로젝트 ID 또는 이슈 ID가 주어지면 해당 정보도 포함됩니다.
    """

    
    if not data.UID == current_user["UID"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create this alert"
        )

    values = data.dict()
    values["A_READ"] = False  # 기본값으로 읽지 않음 설정

    query = alert.insert().values(**values)
    alert_id = await database.execute(query)

    select_query = sa.select(alert).where(alert.c.A_ID == alert_id)
    new_alert = await database.fetch_one(select_query)

    if not new_alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Failed to create alert")
    
    return new_alert

# ✅ 자신이 받은 모든 알림 조회 - 
@router.get("/alerts/view", response_model=List[AlertOut])
async def view_alert(current_user: dict = Depends(get_current_user)):

    """
    사용자가 받은 모든 알림을 조회합니다.
    알림은 사용자가 속한 프로젝트 또는 이슈에 관련된 정보를 포함합니다.
       - 현재 로그인한 사용자의 UID를 기준으로 알림을 조회합니다.
       - 알림은 읽음 여부(A_READ)와 함께 반환됩니다.
    """
    query = alert.select().where(alert.c.UID == current_user["UID"]).order_by(alert.c.A_ID.desc())

    list_alerts = await database.fetch_all(query)

    return list_alerts

# ✅ 알림 읽음으로 변경 -
@router.post("/alerts/read/{alert_id}", response_model=List[AlertOut])
async def set_read_alert(alert_id: int, read: bool = True, current_user: dict = Depends(get_current_user)):

    """
    선택한 알림을 읽음 처리 합니다. 
    """

    query = alert.select(alert).where(
        alert.c.A_ID == alert_id,
        alert.c.UID == current_user["UID"]
    )

    existing_alert = await database.fetch_one(query) # 알람이 존재하는지

    if not existing_alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    
    update_query = alert.update().where(
        alert.c.A_ID == alert_id
    ).values(A_READ=read)

    await database.execute(update_query)

    updated_query = sa.select(alert).where(
        alert.c.A_ID == alert_id
    )

    updated_alert = await database.fetch_one(updated_query)

    return updated_alert

