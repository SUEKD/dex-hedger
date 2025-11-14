import time
from PySide6.QtCore import QThread, Signal, Slot
from core.types import (
    ExchangeId, SupportedSymbol, Direction, OrderType, ExchangeState, Position, LogLevel
)
from core.wrappers.base import BaseExchangeAPI
from typing import Optional, Dict

class AutoBalanceWorker(QThread):
    """
    App.tsx의 checkAutoBalance 로직을 실행하는 스레드.
    주기적으로 A와 B의 포지션을 비교하고 괴리 발생 시 B에 주문을 실행합니다.
    """
    log_message = Signal(str, LogLevel)
    
    # (수정) state_update 시그널을 받아서 상태를 저장
    _state_a: Optional[ExchangeState] = None
    _state_b: Optional[ExchangeState] = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_a: Optional[BaseExchangeAPI] = None
        self.api_b: Optional[BaseExchangeAPI] = None
        self.interval = 3 # 기본값 (초)
        self.is_running = False
        self.symbol: SupportedSymbol = SupportedSymbol.BTC # 기본값

    def set_config(self, api_a: BaseExchangeAPI, api_b: BaseExchangeAPI, interval: float, symbol: SupportedSymbol):
        """스레드 시작 전/후로 설정을 업데이트합니다."""
        self.api_a = api_a
        self.api_b = api_b
        self.interval = interval
        self.symbol = symbol

    def run(self):
        self.is_running = True
        self.log_message.emit(f"[AutoBalance] Worker started. Interval: {self.interval}s", LogLevel.INFO)
        
        while self.is_running:
            if not self.api_a or not self.api_b:
                self.log_message.emit(f"[AutoBalance] Waiting for A and B APIs...", LogLevel.WARN)
                self.sleep(self.interval)
                continue

            if not self._state_a or not self._state_b:
                self.log_message.emit(f"[AutoBalance] Waiting for A and B state data...", LogLevel.WARN)
                self.sleep(self.interval)
                continue
                
            try:
                self.check_balance()
            except Exception as e:
                self.log_message.emit(f"[AutoBalance] Error: {e}", LogLevel.ERROR)
                
            # sleep
            slept_time = 0
            while slept_time < self.interval and self.is_running:
                self.msleep(100) # 0.1초마다 중지 신호 확인
                slept_time += 0.1

    def check_balance(self):
        """App.tsx의 checkAutoBalance 로직"""
        # (상태가 None일 수 있으므로 다시 확인)
        if not self._state_a or not self._state_b:
            return
            
        pos_a = self._state_a.position
        pos_b = self._state_b.position

        # 1. 수량 계산 (롱: +, 숏: -)
        signed_qty_a = 0.0
        if pos_a.direction == Direction.LONG:
            signed_qty_a = pos_a.quantity
        elif pos_a.direction == Direction.SHORT:
            signed_qty_a = -pos_a.quantity

        signed_qty_b = 0.0
        if pos_b.direction == Direction.LONG:
            signed_qty_b = pos_b.quantity
        elif pos_b.direction == Direction.SHORT:
            signed_qty_b = -pos_b.quantity

        # 2. 괴리 (Discrepancy) 계산
        # (A가 기준이므로, B는 A의 반대가 되어야 함. A_qty + B_qty == 0 이어야 함)
        discrepancy = signed_qty_a + signed_qty_b

        # 3. 괴리 발생 시 B거래소에 보정 주문
        # (React 코드의 오차 범위 0.000001 적용)
        if abs(discrepancy) > 0.000001:
            correction_qty = abs(discrepancy)
            # A(롱) + B(롱) = + (괴리 > 0) -> B를 숏
            # A(숏) + B(숏) = - (괴리 < 0) -> B를 롱
            correction_dir = Direction.SHORT if discrepancy > 0 else Direction.LONG
            
            self.log_message.emit(
                f"[AutoBalance] Discrepancy detected (A: {signed_qty_a:.5f}, B: {signed_qty_b:.5f}). "
                f"Balancing on {self.api_b.name}...", LogLevel.WARN
            )
            
            try:
                self.api_b.create_order(
                    symbol=self.symbol,
                    order_type=OrderType.MKT,
                    direction=correction_dir,
                    quantity=correction_qty
                )
                self.log_message.emit(
                    f"[{self.api_b.name}] Auto-balance MKT order submitted: "
                    f"{correction_dir.value} {correction_qty:.5f}", LogLevel.SUCCESS
                )
                # 주문 후 즉시 갱신을 위해 3초 대기 (API가 갱신할 시간)
                self.sleep(3)
                
            except Exception as e:
                self.log_message.emit(f"[{self.api_b.name}] Auto-balance order failed: {e}", LogLevel.ERROR)

    @Slot(ExchangeState, ExchangeState)
    def update_states(self, state_a: Optional[ExchangeState], state_b: Optional[ExchangeState]):
        """main.py로부터 A, B의 최신 상태를 받습니다."""
        self._state_a = state_a
        self._state_b = state_b

    def stop(self):
        self.log_message.emit("[AutoBalance] Worker stopping...", LogLevel.INFO)
        self.is_running = False

# (참고) React의 StrategyWorker는 없음
# React (App.tsx)에서는 전략 주문을 '주문 실행' 버튼 클릭 시 1회성 함수(handleExecuteStrategyOrder)로 처리합니다.
# Python에서는 QThread를 사용할 필요 없이, main.py에서 직접 api_a.create_order()를 호출하면 됩니다.
# 따라서 StrategyWorker는 필요하지 않습니다.

# (참고) React의 StatusWorker도 없음
# React (App.tsx)에서는 useEffect 훅을 사용하여 API 폴링을 시작합니다.
# Python에서는 이 로직을 Mock API (pacifica.py, lighter.py) 내부의 QTimer가
# 직접 담당하므로, 별도의 StatusWorker 스레드가 필요하지 않습니다.