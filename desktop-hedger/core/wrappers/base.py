import sys
from PySide6.QtCore import QObject, Signal
from typing import List, Optional
# (수정) core/types에서 LogLevel, ExchangeId 임포트 추가
from core.types import (
    ApiCredentials, ExchangeState, Order, OrderType, Direction, SupportedSymbol,
    LogLevel, ExchangeId
)

class BaseExchangeAPI(QObject):
    """
    모든 API 래퍼의 공통 인터페이스 (설계도).
    React App.tsx의 ApiClient 인터페이스와 유사하게 작동합니다.
    
    시그널 (Signals):
    - Mock API (QTimer) 또는 실제 API (WebSocket/Polling)가
      데이터를 받으면 이 시그널을 발생시켜 main.py에 알립니다.
    """
    # (React: addLog)
    log_message = Signal(str, LogLevel) # (수정) LogLevel 추가
    
    # (React: setExchangeStates)
    state_update = Signal(ExchangeId, ExchangeState) # (수정) ex_id 추가
    
    # (React: setOpenOrders)
    orders_update = Signal(ExchangeId, list) # (수정) list (List[Order])
    
    # (React: setPrices)
    price_update = Signal(ExchangeId, float) # (수정) ex_id 추가
    
    def __init__(self, ex_id: ExchangeId, name: str, parent=None):
        super().__init__(parent)
        self.client = None # 실제 API SDK 클라이언트 (e.g., PacificaClient)
        self.ex_id = ex_id # 'pacifica'
        self.name = name   # 'Pacifica'

    # --- 1. 연결 (Connect / Auth) ---
    def connect(self, creds: ApiCredentials) -> bool:
        """
        (React: handleSaveApiCreds)
        API 키로 실제 연결을 시도하고, 성공/실패를 반환합니다.
        """
        raise NotImplementedError

    # --- 2. 데이터 스트리밍 (Polling / WebSocket) ---
    def start_streaming(self, symbol: SupportedSymbol):
        """
        (React: useEffect[apiClients])
        인증 성공 후, 해당 심볼의 데이터 폴링/웹소켓을 시작합니다.
        성공 시 state_update, orders_update, price_update 시그널을 발생시킵니다.
        """
        raise NotImplementedError

    def stop_streaming(self):
        """
        (React: useEffect[apiClients] cleanup)
        폴링/웹소켓을 중지합니다.
        """
        raise NotImplementedError

    # --- 3. 주문 실행 (Execute) ---
    
    def set_leverage(self, symbol: SupportedSymbol, leverage: int):
        """
        (React: handleSetLeverage)
        레버리지를 설정합니다.
        """
        raise NotImplementedError

    def create_order(self, symbol: SupportedSymbol, order_type: OrderType, direction: Direction, quantity: float, price: float = None):
        """
        (React: handleExecuteStrategyOrder, handleExecuteIndividualOrder)
        지정가 또는 시장가 주문을 생성합니다.
        """
        raise NotImplementedError

    def cancel_order(self, symbol: SupportedSymbol, order_id: str):
        """
        (React: handleCancelOrder)
        특정 주문을 취소합니다.
        """
        raise NotImplementedError

    def cancel_all_orders(self, symbol: SupportedSymbol):
        """
        (React: handleCancelAllOrders)
        해당 심볼의 모든 미체결 주문을 취소합니다.
        """
        raise NotImplementedError