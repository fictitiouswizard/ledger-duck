from datetime import timedelta, datetime
import secrets
from api import emailduck
from fastapi import Depends, HTTPException, status
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.routing import APIRouter
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from api.schemas import User, RefreshToken
from sqlmodel import Session, select
from api.database import create_session


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshAccessToken(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    username: str | None = None


class RegisterResponse(BaseModel):
    success: bool = False


class RegisterUser(BaseModel):
    username: str = Field(min_length=6, max_length=20)
    email: str = Field(regex=r"^\S+@\S+\.\S+$")
    password: str = Field(min_length=8, regex=r"^(?=.*[A-Z])(?=.*[0-9])(?=.*[a-z]).{8,}$")

    class Config:
        schema_extra = {
            "example": {
                "username": "MyUsername",
                "email": "tester.mctestface@test.test",
                "password": "My5uperSecurePa55word",
            }
        }


class ResetEmail(BaseModel):
    email: str


class ResetPassword(BaseModel):
    token: str
    password: str


# openssl rand -hex 32
SECRET_KEY = "c14db26247efd5539b8b668c44738e6f1fa5dda4df9c7794adc3b34b94e8a6fc"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter(tags=["authentication"])


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user(session: Session, username: str, password: str):
    user = session.exec(select(User).where(User.username == username)).one()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(create_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        # token_data = TokenData(username=username) ?
    except JWTError:
        raise credentials_exception
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(user: User = Depends(get_current_user)):
    if not user.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: int, expires_delta: timedelta | None = None) -> (str, RefreshToken):
    token_secret = secrets.token_urlsafe(32)
    token_data = {"sub": token_secret}
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=30)
    token_data.update({"exp": expire})
    encoded_jwt = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    refresh_token = RefreshToken(user_id=user_id, token=token_secret, valid_until=expire)
    return encoded_jwt, refresh_token


@router.post("/register", response_model=RegisterResponse)
def register_account(*, session: Session = Depends(create_session), registration: RegisterUser):
    username_user = session.exec(select(User).where(User.username == registration.username)).all()
    if username_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username in use")
    email_user = session.exec(select(User).where(User.email == registration.email)).all()
    if email_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email in use")
    hashed_password = get_password_hash(registration.password)
    user = User(username=registration.username, email=registration.email, hashed_password=hashed_password)
    session.add(user)
    session.commit()
    response = RegisterResponse(success=True)
    return response


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(create_session)):
    user = authenticate_user(session=session, username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    refresh_token_str,  refresh_token = create_refresh_token(user_id=user.id)
    session.add(refresh_token)
    session.commit()
    return {"access_token": access_token, "refresh_token": refresh_token_str, "token_type": "bearer"}


@router.post("/refresh", response_model=AccessToken)
async def refresh_access_token(*, session: Session = Depends(create_session), token_data: RefreshAccessToken):
    payload: dict = jwt.decode(token_data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
    token: str = payload.get("sub")
    cmd = select(RefreshToken).where(RefreshToken.token == token)
    try:
        refresh_token = session.exec(cmd).one()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalid")

    cmd = select(User).where(User.id == refresh_token.user_id)
    user = session.exec(cmd).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalid")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    token_response = AccessToken(access_token=access_token)
    return token_response


@router.post("/send_reset_email")
def reset_password_email(
        *,
        session: Session = Depends(create_session),
        reset_email: ResetEmail
):
    cmd = select(User).where(User.email == reset_email.email)
    user = session.exec(cmd).first()
    if not user:
        return Response(status_code=status.HTTP_200_OK)
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    session.add(user)
    session.commit()
    session.refresh(user)
    emailduck.send_password_reset_email(token, user.email)
    return Response(status_code=status.HTTP_200_OK)


@router.post("/reset_password")
def reset_password(
        *,
        session: Session = Depends(create_session),
        password_reset: ResetPassword,
):
    user = session.exec(select(User).where(User.reset_token == password_reset.token)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    user.hashed_password = get_password_hash(password_reset.password)
    user.reset_token = None
    session.add(user)
    session.commit()
    Response(status_code=status.HTTP_200_OK)














