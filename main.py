from fastapi import FastAPI
from app.database import database, engine  # engine은 여기서 가져와야 함
from app.models import metadata            # metadata만 models.py에서 가져오면 됨
from app.routers import user, project, team, issue, auth, alert
app = FastAPI()

# DB 연결
@app.on_event("startup")
async def connect_to_db():
    await database.connect()

# DB 연결 해제
@app.on_event("shutdown")
async def disconnect_from_db():
    await database.disconnect()

# 테이블 생성 (최초 1회만 실행됨)
metadata.create_all(engine)

app.include_router(auth.router)
app.include_router(issue.router)
app.include_router(user.router)
app.include_router(project.router)
app.include_router(team.router)
app.include_router(alert.router)


@app.get("/")
def read_root():
    return {"message": "Hello FastAPI with MariaDB!"}

