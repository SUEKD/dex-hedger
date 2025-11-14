from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List

# types.ts -> export enum ExchangeId
class ExchangeId(Enum):
    PACIFICA = 'pacifica'
    LIGHTER = 'lighter'

# types.ts -> export const EXCHANGE_NAMES
EXCHANGE_NAMES = {
    ExchangeId.PACIFICA: 'Pacifica',
    ExchangeId.LIGHTER: 'Lighter',
}

# types.ts -> export enum Direction
class Direction(Enum):
    LONG = 'LONG'
    SHORT = 'SHORT'
    NONE = 'NONE'

# types.ts -> export enum OrderType
class OrderType(Enum):
    MKT = 'MKT'
    LMT = 'LMT'

# types.ts -> export type SupportedSymbol
class SupportedSymbol(Enum):
    BTC = 'BTC'
    ETH = 'ETH'
    SOL = 'SOL'

# types.ts -> export const SUPPORTED_SYMBOLS
SUPPORTED_SYMBOLS: List[SupportedSymbol] = [SupportedSymbol.BTC, SupportedSymbol.ETH, SupportedSymbol.SOL]

# types.ts -> export interface ApiCredentials
@dataclass
class ApiCredentials:
    apiKey: str
    apiSecret: str
    accountAddress: Optional[str] = None
    accountId: Optional[int] = None
    l1Address: Optional[str] = None

# types.ts -> export interface Position
@dataclass
class Position:
    direction: Direction
    quantity: float
    entryPrice: float

# types.ts -> export interface ExchangeState
@dataclass
class ExchangeState:
    name: str
    position: Position
    pnl: float
    balance: float
    currency: str
    leverage: int

# types.ts -> export interface Order
@dataclass
class Order:
    id: str
    exchangeId: ExchangeId
    type: OrderType
    direction: Direction
    quantity: float
    filledQuantity: float
    price: float
    timestamp: int

# types.ts -> export enum LogLevel
class LogLevel(Enum):
    INFO = 'INFO'
    SUCCESS = 'SUCCESS'
    WARN = 'WARN'
    ERROR = 'ERROR'

# types.ts -> export interface LogEntry
@dataclass
class LogEntry:
    timestamp: str
    level: LogLevel
    message: str