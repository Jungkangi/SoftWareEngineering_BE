import asyncio
from sqlalchemy.exc import OperationalError
from fastapi import FastAPI
from app.database import database, engine  # engine은 여기서 가져와야 함
from app.models import metadata            # metadata만 models.py에서 가져오면 됨
from app.routers import user, project, team, auth, sprint, comment, alert, issue


app = FastAPI()



# ✅ DB 연결
@app.on_event("startup")
async def connect_to_db():
    max_retries = 10
    for attempt in range(max_retries):
        try:
            await database.connect()# ✅ 테이블 생성 (최초 1회만 실행됨)
            metadata.create_all(engine)
            print("✅ DB 연결 성공")
            break
        except OperationalError as e:
            print(f"⏳ DB 연결 실패 (시도 {attempt + 1}/{max_retries}), 재시도 중...")
            await asyncio.sleep(2)
    else:
        raise Exception("❌ DB 연결 실패: 최대 재시도 횟수 초과")

# ✅ DB 연결 해제
@app.on_event("shutdown")
async def disconnect_from_db():
    await database.disconnect()

app.include_router(auth.router)
app.include_router(issue.router)
app.include_router(user.router)
app.include_router(project.router)
app.include_router(team.router)
app.include_router(alert.router)
app.include_router(sprint.router)
app.include_router(comment.router)

@app.get("/")
def read_root():
    return {"message": "Hello FastAPI with MariaDB!"}

