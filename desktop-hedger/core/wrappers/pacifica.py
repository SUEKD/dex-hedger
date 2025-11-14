import sys
import os
import time
import random
import requests 
import hashlib
import hmac
import json
import base58  # (신규) SDK 코드가 파일 내에서 직접 사용
import ed25519 # (신규) SDK 코드가 파일 내에서 직접 사용
from enum import Enum
from datetime import datetime, timezone
from PySide6.QtCore import QTimer, Slot, QObject 

# (수정) 
# 'pacifica_sdk' 폴더를 삭제하는 대신,
# 'pacifica_sdk' 폴더 (원본 rest 폴더)의 모든 내용을
# 이 파일 하나에 모두 합쳤습니다.
# ---------------------------------------------------
# (수정) NameError 해결을 위해 base.py와 core.types 임포트
from .base import BaseExchangeAPI
from core.types import (
    ApiCredentials, ExchangeState, Position, Order, OrderType, Direction, 
    SupportedSymbol, ExchangeId, LogLevel
)
from typing import List
# ---------------------------------------------------

# ---------------------------------------------------
# 시작: pacifica_sdk/enum.py 내용
# ---------------------------------------------------
class OrderSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class PacificaOrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"

class TimeInForce(str, Enum):
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"

class OrderStatus(str, Enum):
    OPEN = "OPEN"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
# ---------------------------------------------------
# 끝: pacifica_sdk/enum.py 내용
# ---------------------------------------------------


# ---------------------------------------------------
# 시작: pacifica_sdk/network.py 내용
# ---------------------------------------------------
class Network(Enum):
    # (수정) 404 오류 해결을 위해 /api/v1 경로 추가
    MAINNET = "https://api.pacifica.fi/api/v1"
    TESTNET = "https://api.testnet.pacifica.fi/api/v1"
# ---------------------------------------------------
# 끝: pacifica_sdk/network.py 내용
# ---------------------------------------------------


# ---------------------------------------------------
# 시작: pacifica_sdk/utils.py 내용
# ---------------------------------------------------
def to_utc_timestamp(dt: datetime) -> int:
    return int(dt.astimezone(timezone.utc).timestamp() * 1000)

def check_api_keys(api_key: str, private_key: str):
    if not api_key:
        raise ValueError("API key is not set")
    if not private_key:
        raise ValueError("Private key is not set")

def create_signature(
    private_key: str, request_str: str, method: str, params
) -> (str, str):
    check_api_keys(api_key="", private_key=private_key)  # private_key만 체크
    
    timestamp = str(to_utc_timestamp(datetime.now()))
    
    # URL 인코딩된 쿼리 문자열 생성 (GET, DELETE)
    query_string = ""
    if method in ["GET", "DELETE"] and params:
        query_string = "&".join(f"{key}={value}" for key, value in sorted(params.items()))
        
    # JSON 문자열 생성 (POST, PUT)
    body_string = ""
    if method in ["POST", "PUT"] and params:
        body_string = json.dumps(params, separators=(',', ':'))

    # 서명할 메시지 구성
    message = timestamp + method + request_str + query_string + body_string
    
    try:
        # private_key(Base58) 디코딩
        private_key_bytes = base58.b58decode(private_key)
        
        # Ed25519 서명 생성
        signing_key = ed25519.SigningKey(private_key_bytes)
        signature_bytes = signing_key.sign(message.encode('utf-8'))
        
        # 서명을 Base58로 인코딩
        signature = base58.b58encode(signature_bytes).decode('utf-8')
        
        return signature, timestamp
    except Exception as e:
        raise ValueError(f"Error creating signature: {e}")
# ---------------------------------------------------
# 끝: pacifica_sdk/utils.py 내용
# ---------------------------------------------------


# ---------------------------------------------------
# 시작: pacifica_sdk/client.py 내용
# ---------------------------------------------------
class Client:
    def __init__(
        self,
        api_key: str,
        private_key: str,
        account_address: str,
        network: Network = Network.MAINNET,
    ):
        check_api_keys(api_key, private_key)
        self.api_key = api_key
        self.private_key = private_key
        self.account_address = account_address
        self.base_url = network.value

    def _request(self, method: str, request_str: str, params=None):
        if params is None:
            params = {}
            
        try:
            signature, timestamp = create_signature(
                self.private_key, request_str, method, params
            )
        except ValueError as e:
            # 서명 생성 실패 시
            return {"error": str(e)}

        headers = {
            "Content-Type": "application/json",
            "X-PACIFICA-API-KEY": self.api_key,
            "X-PACIFICA-SIGNATURE": signature,
            "X-PACIFICA-TIMESTAMP": timestamp,
        }

        url = self.base_url + request_str
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=params)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, params=params)
            else:
                return {"error": f"Unsupported method: {method}"}

            response.raise_for_status()  # 4xx/5xx 오류 시 예외 발생
            return response.json()
        
        except requests.exceptions.HTTPError as http_err:
            # 404, 500, 403 등
            return {"error": f"HTTP Error: {http_err}"}
        except requests.exceptions.RequestException as req_err:
            # 네트워크 오류 (연결 실패 등)
            return {"error": f"Request Error: {req_err}"}
        except json.JSONDecodeError:
            return {"error": "Failed to decode JSON response"}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {e}"}

    # --- Public API ---
    def get_server_time(self):
        return self._request("GET", "/utils/server_time")

    def get_market_summary(self, market_name: str):
        return self._request("GET", f"/markets/{market_name}/summary")

    # --- Private API ---
    def get_collateral(self, token_name: str):
        params = {"token_name": token_name, "account_address": self.account_address}
        return self._request("GET", "/collateral", params=params)

    def update_collateral(self, token_name: str, leverage: int):
        params = {
            "token_name": token_name,
            "account_address": self.account_address,
            "leverage": leverage,
        }
        return self._request("POST", "/collateral", params=params)

    def get_positions(self, market_name: str = None):
        params = {"account_address": self.account_address}
        if market_name:
            params["market_name"] = market_name
        return self._request("GET", "/positions", params=params)

    def get_orders(self, market_name: str, status: str = None):
        params = {"market_name": market_name, "account_address": self.account_address}
        if status:
            params["status"] = status
        return self._request("GET", "/orders", params=params)

    def post_order(
        self,
        market_name: str,
        side: OrderSide,
        order_type: PacificaOrderType,
        order_size: float,
        price_str: str = None, # SDK는 str을 받음
        time_in_force: TimeInForce = TimeInForce.GTC,
        client_order_id: str = None,
        reduce_only: bool = False,
    ):
        params = {
            "market_name": market_name,
            "side": side.value,
            "type": order_type.value,
            "size": order_size,
            "account_address": self.account_address,
            "time_in_force": time_in_force.value,
            "reduce_only": reduce_only,
        }
        if price_str:
            params["price"] = price_str
        if client_order_id:
            params["client_order_id"] = client_order_id
            
        return self._request("POST", "/orders", params=params)

    def delete_order(self, market_name: str, order_id: int): # SDK가 int를 받음
        params = {
            "market_name": market_name,
            "order_id": order_id,
            "account_address": self.account_address,
        }
        return self._request("DELETE", "/orders", params=params)

    def delete_orders(self, market_name: str):
        params = {"market_name": market_name, "account_address": self.account_address}
        return self._request("DELETE", "/orders/all", params=params)
# ---------------------------------------------------
# 끝: pacifica_sdk/client.py 내용
# ---------------------------------------------------


# ---------------------------------------------------
# 시작: pacifica.py (래퍼 클래스)
# ---------------------------------------------------
class PacificaAPI(BaseExchangeAPI):
    """
    Pacifica API의 '실제' 구현.
    QTimer를 사용하여 React 앱의 폴링 로직을 실행합니다.
    """
    def __init__(self, name: str, parent=None):
        super().__init__(ex_id=ExchangeId.PACIFICA, name=name, parent=parent)
        
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_data)
        self.poll_timer.setInterval(3000) # 3초
        
        self.symbol: SupportedSymbol = SupportedSymbol.BTC
        self.market_name: str = "BTC-PERP"

    def connect(self, creds: ApiCredentials) -> bool:
        self.log_message.emit(f"[{self.name}] Connecting with API Key {creds.apiKey[:5]}...", LogLevel.INFO)
        try:
            self.client = Client(
                api_key=creds.apiKey,
                private_key=creds.apiSecret,
                account_address=creds.accountAddress
            )
            
            response = self.client.get_server_time()
            if 'serverTime' in response:
                self.log_message.emit(f"[{self.name}] Connection successful. Server time: {response['serverTime']}", LogLevel.SUCCESS)
                return True
            else:
                # (수정) 404 오류 시, 오류 내용(JSON)을 함께 로깅
                error_msg = response.get('error', 'Unknown error')
                self.log_message.emit(f"[{self.name}] Connection failed: {error_msg}", LogLevel.ERROR)
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
            self._poll_data()
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
            summary_data = self.client.get_market_summary(self.market_name)
            if 'error' in summary_data:
                raise Exception(f"Price poll failed: {summary_data['error']}")
            price = float(summary_data['data']['markPrice'])
            self.price_update.emit(self.ex_id, price)

            # 2. 계정 상태 (State)
            collateral_data = self.client.get_collateral("USDC")
            if 'error' in collateral_data:
                raise Exception(f"Collateral poll failed: {collateral_data['error']}")
                
            position_data = self.client.get_positions(self.market_name)
            if 'error' in position_data:
                raise Exception(f"Position poll failed: {position_data['error']}")

            balance = float(collateral_data['data']['balance'])
            leverage = int(float(collateral_data['data']['leverage'])) 
            
            pos = position_data['data'][0] if position_data['data'] else None
            
            if pos:
                pos_qty = float(pos['positionSize'])
                pos_dir = Direction.LONG if pos['side'] == 'LONG' else Direction.SHORT
                pos_entry = float(pos['entryPrice'])
                pnl = float(pos['unrealisedPnl'])
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
                currency="USDC",
                leverage=leverage
            )
            self.state_update.emit(self.ex_id, state)

            # 3. 미체결 주문 (Open Orders)
            orders_data = self.client.get_orders(market_name=self.market_name, status='OPEN')
            if 'error' in orders_data:
                raise Exception(f"Orders poll failed: {orders_data['error']}")
                
            py_orders: List[Order] = []
            for o in orders_data['data']:
                py_order = Order(
                    id=str(o['orderId']),
                    exchangeId=self.ex_id,
                    type=OrderType.LMT if o['type'] == 'LIMIT' else OrderType.MKT,
                    direction=Direction.LONG if o['side'] == 'LONG' else Direction.SHORT,
                    quantity=float(o['orderSize']),
                    filledQuantity=float(o['filledSize']),
                    price=float(o['price']),
                    timestamp=int(o['createdAt'])
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
            response = self.client.update_collateral(token_name="USDC", leverage=leverage)
            if 'error' in response:
                raise Exception(response['error'])
            self.log_message.emit(f"[{self.name}] Leverage set to {leverage}x.", LogLevel.SUCCESS)
            QTimer.singleShot(500, self._poll_data)
        except Exception as e:
            self.log_message.emit(f"[{self.name}] Set leverage failed: {e}", LogLevel.ERROR)

    def create_order(self, symbol: SupportedSymbol, order_type: OrderType, direction: Direction, quantity: float, price: float = None):
        if not self.client: return
        
        market = f"{symbol.value}-PERP"
        side = OrderSide.LONG if direction == Direction.LONG else OrderSide.SHORT
        sdk_order_type = PacificaOrderType.LIMIT if order_type == OrderType.LMT else PacificaOrderType.MARKET
        
        log_msg = f"[{self.name}] Create {order_type.value} {direction.value} {quantity} @ {price if price else 'MKT'}"
        self.log_message.emit(log_msg, LogLevel.INFO)
        
        try:
            response = self.client.post_order(
                market_name=market,
                side=side,
                order_type=sdk_order_type,
                order_size=quantity,
                price_str=str(price) if price else None,
            )
            if 'error' in response:
                raise Exception(response['error'])
            self.log_message.emit(f"[{self.name}] Order submitted successfully.", LogLevel.SUCCESS)
            QTimer.singleShot(500, self._poll_data) 
        except Exception as e:
            self.log_message.emit(f"[{self.name}] Order creation failed: {e}", LogLevel.ERROR)


    def cancel_order(self, symbol: SupportedSymbol, order_id: str):
        if not self.client: return
        self.log_message.emit(f"[{self.name}] Cancelling order: {order_id}", LogLevel.INFO)
        try:
            market = f"{symbol.value}-PERP"
            response = self.client.delete_order(market_name=market, order_id=int(order_id)) 
            if 'error' in response:
                raise Exception(response['error'])
            self.log_message.emit(f"[{self.name}] Order {order_id} cancelled.", LogLevel.SUCCESS)
            QTimer.singleShot(500, self._poll_data)
        except Exception as e:
            self.log_message.emit(f"[{self.name}] Cancel order failed: {e}", LogLevel.ERROR)

    def cancel_all_orders(self, symbol: SupportedSymbol):
        if not self.client: return
        self.log_message.emit(f"[{self.name}] Cancelling ALL orders for {symbol.value}...", LogLevel.WARN)
        try:
            market = f"{symbol.value}-PERP"
            response = self.client.delete_orders(market_name=market)
            if 'error' in response:
                raise Exception(response['error'])
            self.log_message.emit(f"[{self.name}] All orders cancelled.", LogLevel.SUCCESS)
            QTimer.singleShot(500, self._poll_data)
        except Exception as e:
            self.log_message.emit(f"[{self.name}] Cancel all orders failed: {e}", LogLevel.ERROR)