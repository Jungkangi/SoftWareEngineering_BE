from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.database import database
from app.models import user
from app.auth import verify_password, create_access_token
import sqlalchemy as sa

router = APIRouter()

class LoginRequest(BaseModel):
    UID: str
    PASSWORD: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    query = sa.text("SELECT * FROM USER WHERE UID = :uid").bindparams(uid=data.UID)
    result = await database.fetch_one(query)

    if result is None:
        raise HTTPException(status_code=401, detail="사용자 없음")

    user_data = dict(result)  # Row -> dict

    print("user_data 전체:", dict(user_data))
    print("nickname:", user_data["NICKNAME"])


    if not verify_password(data.PASSWORD, user_data["PASSWORD"]):
        raise HTTPException(status_code=401, detail="비밀번호 틀림")

    token = create_access_token(user_data["UID"], user_data["NICKNAME"])

    return {"access_token": token}
