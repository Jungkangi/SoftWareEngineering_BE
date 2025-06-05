from fastapi import APIRouter, HTTPException, Depends, status
from datetime import datetime # create_alert에서 사용하지 않으면 제거 가능
from pydantic import BaseModel, Field
from typing import List, Optional
import sqlalchemy as sa
from enum import Enum # Enum import 추가 (AlertTypeEnum이 여기에 정의되어 있다면)

from app.database import database
from app.dependencies import get_current_user
from app.models import alert # SQLAlchemy Table 객체
# from app.models import AlertTypeEnum # 만약 AlertTypeEnum이 models.py에 정의되어 있다면

router = APIRouter()

# AlertTypeEnum 정의 (이 파일 또는 app.models에 정의)
# DB 스키마의 ENUM 값과 일치해야 합니다.
class AlertTypeEnum(str, Enum): # 이미 app.models에 있다면 중복 정의 불필요
    TEAM_INVITE = "TEAM_INVITE"
    ISSUE_NOTIFICATION = "ISSUE_NOTIFICATION"
    ISSUE_DEADLINE_NEAR = "ISSUE_DEADLINE_NEAR"
    ISSUE_DEADLINE_OVER = "ISSUE_DEADLINE_OVER"


# ✅ 요청용 스키마: 클라이언트가 보낼 데이터 형식 정의 (이전과 동일)
class AlertCreate(BaseModel):
    A_CATEGORY: AlertTypeEnum
    A_CONTENT: str
    UID: str  # 알림 수신자 UID
    P_ID: Optional[int] = None
    I_ID: Optional[int] = None

# ✅ 응답용 스키마: DB 스키마에 맞춰 수정
class AlertOut(BaseModel):
    A_ID: int # PK 추가
    A_CATEGORY: AlertTypeEnum
    A_CONTENT: str
    A_READ: bool
    UID: Optional[str] = None # DB에서 NULL일 수 있으므로 Optional, 수신자 UID
    P_ID: Optional[int] = None
    I_ID: Optional[int] = None
    # A_CREATED_AT 필드는 DB 스키마에 없으므로 제거 (또는 추가 시 DB 스키마 변경 필요)

    class Config:
        from_attributes = True # Pydantic V2 (또는 orm_mode = True for V1)


###########################################################################

# ✅ 알림 생성 - 완
@router.post("/alerts/create", response_model=List[AlertOut]) # 1. GET -> POST로 변경
async def create_alert(data: AlertCreate, current_user: dict = Depends(get_current_user)):
    """
    새로운 알림을 생성합니다.
    - 알림 수신자는 요청 바디의 UID로 설정됩니다.
    - 프로젝트 ID 또는 이슈 ID가 주어지면 해당 정보도 포함됩니다.
    """

    # 2. DB에 INSERT할 값 준비 (컬럼명 일치 및 Enum 값 처리)
    insert_values = {
        "A_CATEGORY": data.A_CATEGORY.value, # Enum의 실제 값 저장
        "A_CONTENT": data.A_CONTENT,
        "UID": data.UID,  # 알림 수신자 UID (DB의 'UID' 컬럼에 해당)
        "P_ID": data.P_ID,
        "I_ID": data.I_ID,
        "A_READ": False,  # 기본값 (DB 스키마에도 default=False 명시됨)
        # "AUTHOR_UID" 같은 컬럼은 DB 스키마에 없으므로 current_user["UID"]를 직접 저장하지 않음
    }

    # app.models.alert는 SQLAlchemy Table 객체여야 함
    query = alert.insert().values(**insert_values)

    try:
        # 3. database.execute()는 보통 생성된 레코드의 PK를 반환
        last_record_id = await database.execute(query)
    except Exception as e:
        print(f"Database insert error: {e}") # 로깅
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create alert.")

    if not last_record_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create alert, no ID returned.")

    # 4. 생성된 알림을 다시 조회하여 AlertOut 형태로 반환
    select_query = alert.select().where(alert.c.A_ID == last_record_id)
    created_alert_record = await database.fetch_one(select_query)

    if not created_alert_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Newly created alert not found.")

    # 5. AlertOut 모델로 변환하여 리스트로 반환
    return [AlertOut.model_validate(created_alert_record)]


# ✅ 자신이 받은 모든 알림 조회 - 완
@router.get("/alerts/view", response_model=List[AlertOut])
async def view_alert(current_user: dict = Depends(get_current_user)):
    """
    현재 로그인한 사용자가 받은 모든 알림을 조회합니다. (수신자 기준)
    """
    query = alert.select().where(alert.c.UID == current_user["UID"]).order_by(alert.c.A_ID.desc())
    db_alerts = await database.fetch_all(query)

    # 6. DB 레코드 리스트를 AlertOut 모델 객체의 리스트로 변환
    return [AlertOut.model_validate(db_alert_record) for db_alert_record in db_alerts]


# ✅ 알림 읽음으로 변경 - 수정 필요 (response_model 및 반환값 모델 변환)
@router.post("/alerts/read/{alert_id}", response_model=AlertOut) # 7. response_model을 List[AlertOut] -> AlertOut으로 변경
async def set_read_alert(alert_id: int, read: bool = True, current_user: dict = Depends(get_current_user)):
    """
    선택한 알림을 읽음/안읽음 처리 합니다.
    본인에게 온 알림만 처리 가능합니다.
    """

    # 알림이 존재하고, 현재 사용자가 수신자인지 확인
    query = alert.select().where(
        (alert.c.A_ID == alert_id) &
        (alert.c.UID == current_user["UID"]) # 본인 알림만 수정 가능하도록 조건 추가
    )
    existing_alert_record = await database.fetch_one(query)

    if not existing_alert_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or you do not have permission to modify this alert."
        )

    update_query = alert.update().where(
        alert.c.A_ID == alert_id
    ).values(A_READ=read)

    await database.execute(update_query)

    # 업데이트된 알림 정보를 다시 조회하여 반환
    updated_query = alert.select().where(alert.c.A_ID == alert_id)
    updated_alert_record = await database.fetch_one(updated_query)

    if not updated_alert_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Updated alert could not be retrieved.")

    # 8. DB 레코드를 AlertOut 모델 객체로 변환하여 반환
    return AlertOut.model_validate(updated_alert_record)