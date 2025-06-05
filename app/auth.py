from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

# 환경 설정
SECRET_KEY = "1234"  # ⚠️ 실제 환경에서는 .env로 관리
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 3000

# 비밀번호 암호화용 context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 비밀번호 검증 함수
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# 비밀번호 해시 함수
def get_password_hash(password):
    return pwd_context.hash(password)

# JWT 토큰 생성 함수
def create_access_token(uid: str, nickname: str, expires_delta: timedelta | None = None):
    to_encode = {
        "sub": uid,
        "nickname": nickname,
        "exp": datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# JWT 토큰 검증 함수
def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
