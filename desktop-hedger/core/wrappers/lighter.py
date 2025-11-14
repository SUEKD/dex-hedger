import sys
import os
import time
import random
import requests 
import hmac # (신규) Lighter SDK가 사용
import hashlib # (신규) Lighter SDK가 사용
import json # (신규) Lighter SDK가 사용
from PySide6.QtCore import QTimer, Slot, QObject 
from typing import List, Dict, Any # (신규) Lighter SDK가 사용

# (수정) 
# 'lighter' 폴더를 삭제하는 대신,
# 'lighter' 폴더 (원본 lighter-python)의 모든 내용을
# 이 파일 하나에 모두 합쳤습니다.
# ---------------------------------------------------
# (수정) BaseExchangeAPI / core.types 임포트 추가
from .base import BaseExchangeAPI
from core.types import (
    ApiCredentials, ExchangeState, Position, Order, OrderType, Direction, 
    SupportedSymbol, ExchangeId, LogLevel
)
# ---------------------------------------------------


# ---------------------------------------------------
# 시작: lighter/classes.py 내용
# ---------------------------------------------------
class LighterOrderBook:
    def __init__(self, data: Dict[str, Any]):
        self.bids = [LighterPriceLevel(bid) for bid in data["bids"]]
        self.asks = [LighterPriceLevel(ask) for ask in data["asks"]]

class LighterPriceLevel:
    def __init__(self, data: List[Any]):
        self.price = float(data[0])
        self.size = float(data[1])
# ---------------------------------------------------
# 끝: lighter/classes.py 내용
# ---------------------------------------------------


# ---------------------------------------------------
# 시작: lighter/client.py 내용
# ---------------------------------------------------
class Client:
    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        account_id: str = None,
        l1_address: str = None,
        base_url: str = "https://mainnet.zklighter.elliot.ai",
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.account_id = account_id
        self.l1_address = l1_address
        self.base_url = base_url

    def _get(self, endpoint: str, params: dict = None) -> dict:
        url = self.base_url + endpoint
        response = requests.get(url, params=params)
        return self._handle_response(response)

    def _post(self, endpoint: str, data: dict = None) -> dict:
        url = self.base_url + endpoint
        headers = self._get_auth_headers("POST", endpoint, data)
        response = requests.post(url, headers=headers, json=data)
        return self._handle_response(response)

    def _delete(self, endpoint: str, data: dict = None) -> dict:
        url = self.base_url + endpoint
        headers = self._get_auth_headers("DELETE", endpoint, data)
        response = requests.delete(url, headers=headers, json=data)
        return self._handle_response(response)

    def _get_auth_headers(self, method: str, endpoint: str, data: dict = None) -> dict:
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret must be set for private endpoints")

        timestamp = str(int(time.time() * 1000))
        body = json.dumps(data) if data else ""
        
        # (수정) Lighter의 시그니처 생성 방식 (TS 코드 참고)
        # message = timestamp + method + endpoint + body
        message = f"{timestamp}{method.upper()}{endpoint}{body}"
        
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return {
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key,
            "X-Timestamp": timestamp,
            "X-Signature": signature,
        }

    def _handle_response(self, response: requests.Response) -> dict:
        try:
            response.raise_for_status() # 4xx, 5xx 에러 시 예외 발생
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            # (수정) Lighter가 오류 메시지를 json으로 반환함
            try:
                error_data = response.json()
                error_msg = error_data.get('error', str(http_err))
            except json.JSONDecodeError:
                error_msg = str(http_err)
            raise Exception(f"HTTP error occurred: {error_msg}") from http_err
        except Exception as err:
            raise Exception(f"Other error occurred: {err}") from err

    # Public Endpoints
    def get_server_time(self) -> dict:
        return self._get("/api/v2/time")
        
    def get_market_price(self, market_name: str) -> dict:
        # (수정) TS 코드의 getPublicPrice 참고
        data = self._get(f"/api/v2/market/summary?market={market_name}")
        # (수정) Pacifica와 유사하게 'price' 키를 갖도록 가공
        if data and 'mark_price' in data:
            return {'price': data['mark_price']}
        raise Exception(f"Price not found in response: {data}")

    def get_orderbook(self, market_name: str) -> LighterOrderBook:
        # (수정) v1 -> v2
        data = self._get(f"/api/v2/market/orderbook?market={market_name}")
        return LighterOrderBook(data)

    # Private Endpoints
    def get_account_collateral(self, token_name: str) -> dict:
        # (수정) v1 -> v2
        endpoint = f"/api/v2/account/collateral"
        headers = self._get_auth_headers("GET", endpoint)
        
        # (수정) Client 생성 시 account_id가 설정되었으므로 params에 추가
        params = {"token": token_name, "account_id": self.account_id}
        
        url = self.base_url + endpoint
        response = requests.get(url, headers=headers, params=params)
        return self._handle_response(response)

    def update_collateral(self, token_name: str, leverage: str) -> dict:
        # (수정) v1 -> v2
        endpoint = f"/api/v2/account/collateral"
        data = {
            "account_id": self.account_id,
            "token": token_name,
            "leverage": leverage,
        }
        return self._post(endpoint, data=data)

    def get_positions(self, market_name: str) -> dict:
        # (수정) v1 -> v2
        endpoint = f"/api/v2/account/positions"
        headers = self._get_auth_headers("GET", endpoint)
        params = {"market": market_name, "account_id": self.account_id}
        
        url = self.base_url + endpoint
        response = requests.get(url, headers=headers, params=params)
        # (수정) 포지션은 리스트가 아닌 단일 객체로 반환됨 (TS 코드 참고)
        data = self._handle_response(response)
        return data # (데이터가 없으면 비어있는 dict {} 반환)

    def get_orders(self, market_name: str, status: str = "OPEN") -> List[dict]:
        # (수정) v1 -> v2
        endpoint = f"/api/v2/account/orders"
        headers = self._get_auth_headers("GET", endpoint)
        params = {"market": market_name, "account_id": self.account_id}
        
        url = self.base_url + endpoint
        response = requests.get(url, headers=headers, params=params)
        all_orders = self._handle_response(response)
        
        # (수정) Lighter SDK는 status 필터링을 지원하지 않으므로, 직접 필터링
        if status == "OPEN":
            return [o for o in all_orders if o.get('status') == 'OPEN']
        return all_orders


    def post_order(
        self,
        market_name: str,
        side: str, # 'B' (Buy) or 'S' (Sell)
        order_type: str, # 'L' (Limit) or 'M' (Market)
        size: str,
        price: str = None,
    ) -> dict:
        # (수정) v1 -> v2
        endpoint = f"/api/v2/account/orders"
        data = {
            "account_id": self.account_id,
            "market": market_name,
            "side": side,
            "type": order_type,
            "size": size,
        }
        if price:
            data["price"] = price
        
        return self._post(endpoint, data=data)

    def delete_order(self, market_name: str, order_id: int) -> dict:
        # (수정) v1 -> v2
        endpoint = f"/api/v2/account/orders"
        data = {
            "account_id": self.account_id,
            "market": market_name,
            "order_id": order_id,
        }
        return self._delete(endpoint, data=data)

    def delete_orders(self, market_name: str) -> dict:
        # (수정) v1 -> v2
        endpoint = f"/api/v2/account/orders/all"
        data = {"account_id": self.account_id, "market": market_name}
        return self._delete(endpoint, data=data)
# ---------------------------------------------------
# 끝: lighter/client.py 내용
# ---------------------------------------------------


# ---------------------------------------------------
# 시작: Python 래퍼 클래스 (LighterAPI)
# ---------------------------------------------------
class LighterAPI(BaseExchangeAPI):
    """
    (수정) Lighter API의 '실제' 구현.
    QTimer를 사용하여 React 앱의 폴링 로직을 실행합니다.
    """
    def __init__(self, name: str, parent=None):
        super().__init__(ex_id=ExchangeId.LIGHTER, name=name, parent=parent)
        
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_data)
        self.poll_timer.setInterval(3100) # 3.1초
        
        self.symbol: SupportedSymbol = SupportedSymbol.BTC
        self.market_name: str = "BTC-PERP" 

    def connect(self, creds: ApiCredentials) -> bool:
        self.log_message.emit(f"[{self.name}] Connecting with API Key {creds.apiKey[:5]}...", LogLevel.INFO)
        if not creds.accountId or not creds.l1Address:
            self.log_message.emit(f"[{self.name}] Connection failed: Lighter requires Account ID and L1 Address.", LogLevel.ERROR)
            return False
            
        try:
            self.client = Client(
                api_key=creds.apiKey,
                api_secret=creds.apiSecret,
                account_id=str(creds.accountId), 
                l1_address=creds.l1Address
            )
            
            response = self.client.get_account_collateral("USDT")
            
            if response and 'balance' in response:
                self.log_message.emit(f"[{self.name}] Connection successful. Balance: {response['balance']}", LogLevel.SUCCESS)
                return True
            else:
                self.log_message.emit(f"[{self.name}] Connection failed: {response}", LogLevel.ERROR)
                self.client = None
                return False
        except Exception as e:
            self.log_message.emit(f"[{self.name}] Connection error: {e}", LogLevel.ERROR)
            self.client = None
            return False

    def start_streaming(self, symbol: SupportedSymbol):
        if not self.client:
            self.log_message.emit(f"[{self.name}] Cannot start streaming: Not connected.", LogLevel.ERROR)
            return

        self.symbol = symbol
        self.market_name = f"{symbol.value}-PERP"
        self.log_message.emit(f"[{self.name}] Real-data polling started for {self.market_name}...", LogLevel.INFO)
        
        if not self.poll_timer.isActive():
            self._poll_data() # 즉시 1회 호출
            self.poll_timer.start()

    def stop_streaming(self):
        self.log_message.emit(f"[{self.name}] Real-data polling stopped.", LogLevel.INFO)
        self.poll_timer.stop()

    @Slot()
    def _poll_data(self):
        """
        QTimer에 의해 호출되어 '실제' 데이터를 가져옵니다.
        """
        if not self.client or not self.poll_timer.isActive():
            self.stop_streaming()
            return

        try:
            # 1. 가격 (Price)
            price_data = self.client.get_market_price(self.market_name)
            price = float(price_data['price'])
            self.price_update.emit(self.ex_id, price)

            # 2. 계정 상태 (State)
            collateral_data = self.client.get_account_collateral("USDT") # (Lighter는 USDT 가정)
            position_data = self.client.get_positions(self.market_name)
            
            balance = float(collateral_data['balance'])
            leverage = int(float(collateral_data['leverage']))
            
            if position_data and float(position_data['size']) > 0:
                pos_qty = float(position_data['size'])
                pos_dir = Direction.LONG if position_data['side'] == 'B' else Direction.SHORT # (B/S)
                pos_entry = float(position_data['entry_price'])
                pnl = float(position_data['unrealised_pnl'])
            else:
                pos_qty = 0.0
                pos_dir = Direction.NONE
                pos_entry = 0.0
                pnl = 0.0

            state = ExchangeState(
                name=self.name,
                position=Position(direction=pos_dir, quantity=pos_qty, entryPrice=pos_entry),
                pnl=pnl,
                balance=balance,
                currency="USDT",
                leverage=leverage
            )
            self.state_update.emit(self.ex_id, state)

            # 3. 미체결 주문 (Open Orders)
            orders_data = self.client.get_orders(market_name=self.market_name, status='OPEN')
            
            py_orders: List[Order] = []
            for o in orders_data:
                py_order = Order(
                    id=str(o['order_id']),
                    exchangeId=self.ex_id,
                    type=OrderType.LMT if o['type'] == 'L' else OrderType.MKT, # (L/M)
                    direction=Direction.LONG if o['side'] == 'B' else Direction.SHORT, # (B/S)
                    quantity=float(o['size']),
                    filledQuantity=float(o['filled_size']),
                    price=float(o['price']),
                    timestamp=int(o['created_at'])
                )
                py_orders.append(py_order)
                
            self.orders_update.emit(self.ex_id, py_orders)

        except requests.exceptions.RequestException as e:
            self.log_message.emit(f"[{self.name}] Network error during poll: {e}", LogLevel.ERROR)
            self.stop_streaming()
        except Exception as e:
            self.log_message.emit(f"[{self.name}] Data poll failed: {e}", LogLevel.ERROR)


    def set_leverage(self, symbol: SupportedSymbol, leverage: int):
        if not self.client: return
        self.log_message.emit(f"[{self.name}] Setting leverage to {leverage}x...", LogLevel.INFO)
        try:
            self.client.update_collateral(token_name="USDT", leverage=str(leverage)) 
            self.log_message.emit(f"[{self.name}] Leverage set to {leverage}x.", LogLevel.SUCCESS)
            QTimer.singleShot(500, self._poll_data)
        except Exception as e:
            self.log_message.emit(f"[{self.name}] Set leverage failed: {e}", LogLevel.ERROR)

    def create_order(self, symbol: SupportedSymbol, order_type: OrderType, direction: Direction, quantity: float, price: float = None):
        if not self.client: return
        
        market = f"{symbol.value}-PERP"
        side = 'B' if direction == Direction.LONG else 'S'
        sdk_order_type = 'L' if order_type == OrderType.LMT else 'M'
        
        log_msg = f"[{self.name}] Create {order_type.value} {direction.value} {quantity} @ {price if price else 'MKT'}"
        self.log_message.emit(log_msg, LogLevel.INFO)
        
        try:
            self.client.post_order(
                market_name=market,
                side=side,
                order_type=sdk_order_type,
                size=str(quantity), 
                price=str(price) if price else None, 
            )
            self.log_message.emit(f"[{self.name}] Order submitted successfully.", LogLevel.SUCCESS)
            QTimer.singleShot(500, self._poll_data)
        except Exception as e:
            self.log_message.emit(f"[{self.name}] Order creation failed: {e}", LogLevel.ERROR)


    def cancel_order(self, symbol: SupportedSymbol, order_id: str):
        if not self.client: return
        self.log_message.emit(f"[{self.name}] Cancelling order: {order_id}", LogLevel.INFO)
        try:
            market = f"{symbol.value}-PERP"
            self.client.delete_order(market_name=market, order_id=int(order_id)) 
            self.log_message.emit(f"[{self.name}] Order {order_id} cancelled.", LogLevel.SUCCESS)
            QTimer.singleShot(500, self._poll_data)
        except Exception as e:
            self.log_message.emit(f"[{self.name}] Cancel order failed: {e}", LogLevel.ERROR)

    def cancel_all_orders(self, symbol: SupportedSymbol):
        if not self.client: return
        self.log_message.emit(f"[{self.name}] Cancelling ALL orders for {symbol.value}...", LogLevel.WARN)
        try:
            market = f"{symbol.value}-PERP"
            self.client.delete_orders(market_name=market)
            self.log_message.emit(f"[{self.name}] All orders cancelled.", LogLevel.SUCCESS)
            QTimer.singleShot(500, self._poll_data)
        except Exception as e:
            self.log_message.emit(f"[{self.name}] Cancel all orders failed: {e}", LogLevel.ERROR)