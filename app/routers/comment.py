# app/routers/comment.py

from fastapi import APIRouter, HTTPException, Depends, Path
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.models import comment
from app.database import database
from app.dependencies import get_current_user

router = APIRouter()

# 🔹 댓글 생성 요청
class CommentCreate(BaseModel):
    CONTENT: str = Field(..., max_length=500)

# 🔹 댓글 응답 모델
class CommentOut(CommentCreate):
    C_ID: int
    UID: str
    REF_TYPE: str
    REF_ID: int
    CREATE_DATE: Optional[datetime] = None  # ← 이렇게 변경


# ✅ 댓글 작성
@router.post("/comments/{ref_type}/{ref_id}", response_model=CommentOut)
async def create_comment(
    ref_type: str,
    ref_id: int,
    data: CommentCreate,
    current_user: dict = Depends(get_current_user)
):
    values = {
        "REF_TYPE": ref_type.upper(),
        "REF_ID": ref_id,
        "UID": current_user["UID"],
        "CONTENT": data.CONTENT, 
        "CREATE_DATE": datetime.now()
    }
    query = comment.insert().values(**values)
    new_id = await database.execute(query)

    # 생성된 댓글의 전체 정보를 조회하여 반환
    created_comment = await database.fetch_one(
        comment.select().where(comment.c.C_ID == new_id)
    )

    return created_comment


# ✅ 특정 항목의 댓글 조회
@router.get("/comments/{ref_type}/{ref_id}", response_model=List[CommentOut])
async def get_comments(ref_type: str, ref_id: int):
    query = comment.select().where(
        comment.c.REF_TYPE == ref_type.upper(),
        comment.c.REF_ID == ref_id
    )
    return await database.fetch_all(query)

# ✅ 댓글 삭제
@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    current_user: dict = Depends(get_current_user)
):
    # 1. 댓글 존재 및 소유자 확인
    existing = await database.fetch_one(
        comment.select().where(comment.c.C_ID == comment_id)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="댓글이 존재하지 않습니다.")

    if existing["UID"] != current_user["UID"]:
        raise HTTPException(status_code=403, detail="본인의 댓글만 삭제할 수 있습니다.")

    # 2. 삭제 실행
    delete_query = comment.delete().where(comment.c.C_ID == comment_id)
    await database.execute(delete_query)

    return {"message": f"댓글 {comment_id}가 삭제되었습니다."}
