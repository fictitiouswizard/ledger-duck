import datetime
import enum

from sqlmodel import SQLModel, Field, Relationship


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
    id: int | None = Field(default=None, primary_key=True)

    user_id: int = Field(foreign_key="user.id")
    transactions: list["Transaction"] = Relationship(back_populates="account")
    user: "User" = Relationship(back_populates="accounts")


class CreateAccount(BaseAccount):
    pass


class ReadAccount(BaseAccount):
    id: int


class BaseCategory(SQLModel):
    name: str


class Category(BaseCategory, table=True):
    id: int | None = Field(default=None, primary_key=True)

    user_id: int = Field(foreign_key="user.id")
    transactions: list["Transaction"] = Relationship(back_populates="category")
    user: "User" = Relationship(back_populates="categories")


class CreateCategory(BaseCategory):
    pass


class ReadCategory(BaseCategory):
    id: int


class BaseTransaction(SQLModel):
    memo: str
    amount: float
    transaction_date: datetime.datetime
    transaction_type: TransactionType


class Transaction(BaseTransaction, table=True):
    id: int | None = Field(default=None, primary_key=True)

    account_id: int = Field(foreign_key="account.id")
    category_id: int = Field(foreign_key="category.id")
    user_id: int = Field(foreign_key="user.id")
    account: Account = Relationship(back_populates="transactions")
    category: Category = Relationship(back_populates="transactions")
    user: "User" = Relationship(back_populates="transactions")


class ReadTransaction(BaseTransaction):
    id: int
    account: Account
    category: Category


class CreateTransaction(BaseTransaction):
    account_id: int
    category_id: int


class CreateAccountTransaction(BaseTransaction):
    category_id: int


class BaseUser(SQLModel):
    email: str = Field(unique=True)
    username: str = Field(unique=True)
    locked: bool = False
    active: bool = True


class User(BaseUser, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str

    transactions: list[Transaction] = Relationship(back_populates="user")
    categories: list[Category] = Relationship(back_populates="user")
    accounts: list[Account] = Relationship(back_populates="user")
