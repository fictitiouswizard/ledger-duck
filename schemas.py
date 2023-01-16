import datetime
import enum
from sqlmodel import SQLModel, Field, Relationship
import uuid


class TransactionType(str, enum.Enum):
    Debit = "debit"
    Check = "check"
    Deposit = "deposit"
    ATM = "atm"
    Auto = "automatic"
    Transfer = "transfer"
    Adjustment = "adjustment"


class BaseAccount(SQLModel):
    name: str


class Account(BaseAccount, table=True):
    id: uuid.UUID = Field(
        primary_key=True,
        default_factory=uuid.uuid4,
        index=True,
        nullable=False
    )
    active: bool = Field(default=True)

    user_id: int = Field(foreign_key="user.id")
    transactions: list["Transaction"] = Relationship(back_populates="account")
    user: "User" = Relationship(back_populates="accounts")


class CreateAccount(BaseAccount):
    pass


class ReadAccount(BaseAccount):
    id: int


class UpdateAccount(SQLModel):
    active: bool | None
    name: str | None


class BaseCategory(SQLModel):
    name: str


class Category(BaseCategory, table=True):
    id: uuid.UUID = Field(
        primary_key=True,
        default_factory=uuid.uuid4,
        index=True,
        nullable=False
    )
    active: bool = Field(default=True)

    user_id: int = Field(foreign_key="user.id")
    transactions: list["Transaction"] = Relationship(back_populates="category")
    user: "User" = Relationship(back_populates="categories")


class CreateCategory(BaseCategory):
    pass


class ReadCategory(BaseCategory):
    id: int


class UpdateCategory(SQLModel):
    active: bool | None
    name: str | None


class BaseTransaction(SQLModel):
    memo: str
    amount: float
    transaction_date: datetime.datetime
    transaction_type: TransactionType
    description: str | None
    transaction_id: str | None


class Transaction(BaseTransaction, table=True):
    id: uuid.UUID = Field(
        primary_key=True,
        default_factory=uuid.uuid4,
        index=True,
        nullable=False
    )
    active: bool = Field(default=True)

    account_id: int = Field(foreign_key="account.id")
    category_id: int = Field(foreign_key="category.id")
    user_id: int = Field(foreign_key="user.id")
    bill_id: int | None = Field(default=None, foreign_key="bill.id")
    account: Account = Relationship(back_populates="transactions")
    category: Category = Relationship(back_populates="transactions")
    user: "User" = Relationship(back_populates="transactions")
    bill: "Bill" = Relationship(back_populates="transactions")


class UpdateTransaction(SQLModel):
    active: bool | None
    memo: str | None
    amount: float | None
    transaction_date: datetime.datetime | None
    transaction_type: TransactionType | None
    description: str | None
    transaction_id: str | None
    category_id: int | None
    bill_id: int | None


class CreateTransaction(BaseTransaction):
    account_id: int
    category_id: int
    bill_id: int | None = Field(default=None)


class CreateAccountTransaction(BaseTransaction):
    category_id: int


class BaseUser(SQLModel):
    email: str = Field(unique=True)
    username: str = Field(unique=True)
    locked: bool = False
    active: bool = True


class User(BaseUser, table=True):
    id: uuid.UUID = Field(
        primary_key=True,
        default_factory=uuid.uuid4,
        index=True,
        nullable=False
    )
    hashed_password: str
    reset_token: str | None = Field(default=None)

    transactions: list[Transaction] = Relationship(back_populates="user")
    categories: list[Category] = Relationship(back_populates="user")
    accounts: list[Account] = Relationship(back_populates="user")
    bills: list["Bill"] = Relationship(back_populates="user")


class BaseBill(SQLModel):
    name: str
    amount: float
    due_date: int
    description: str | None
    auto: bool = Field(default=False)
    payment_account: str | None


class Bill(BaseBill, table=True):
    id: uuid.UUID = Field(
        primary_key=True,
        default_factory=uuid.uuid4,
        index=True,
        nullable=False
    )
    active: bool = Field(default=True)

    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="bills")
    transactions: list[Transaction] = Relationship(back_populates="bill")


class CreateBill(BaseBill):
    pass


class ReadBill(BaseBill):
    active: bool


class UpdateBill(SQLModel):
    name: str | None
    amount: float | None
    due_date: int | None
    description: str | None
    auto: bool | None
    payment_account: str | None
    active: bool | None


class ReadTransaction(BaseTransaction):
    id: int
    account: Account
    category: Category
    bill: Bill | None


class RefreshToken(SQLModel, table=True):
    id: uuid.UUID = Field(
        primary_key=True,
        default_factory=uuid.uuid4,
        index=True,
        nullable=False
    )
    token: str
    user_id: int
    active: bool = Field(default=True)
    valid_until: datetime.datetime
