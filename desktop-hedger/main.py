import sys
import os
import json
import logging 
import time
from PySide6.QtCore import (
    Qt, QThread, Signal, Slot, QSettings, QTimer, QSize, QPoint
)
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QComboBox, QFrame, QGridLayout,
    QSizePolicy, QCheckBox, QListWidget, QListWidgetItem, QStackedWidget,
    QSplitter, QTextEdit, QDialog, QDialogButtonBox, QSpinBox, QDoubleSpinBox,
    QTableWidget, QHeaderView, QAbstractItemView, QTableWidgetItem
)
from typing import Dict, List, Optional

# --- Config ---
from config import CONFIG_FILE

# --- Core Types (from types.ts) ---
from core.types import (
    ExchangeId, EXCHANGE_NAMES, Direction, OrderType, SupportedSymbol,
    SUPPORTED_SYMBOLS, ApiCredentials, Position, ExchangeState, Order,
    LogLevel, LogEntry
)

# --- UI Widgets (from common/) ---
from ui.widgets import Card, IconLabel, ToggleSwitch, StackedInput, LoadingIndicator, LabeledInput

# --- Core Wrappers (API) ---
from core.wrappers import EXCHANGE_MAP, EXCHANGE_ID_MAP
from core.wrappers.base import BaseExchangeAPI

# --- Core Workers (Logic) ---
from core.workers import AutoBalanceWorker

# --- 
# React의 Tailwind CSS 스타일을 PySide6 QSS로 번역한 스타일시트
# (bg-gray-800, text-xs, text-cyan-400 등)
# ---
STYLESHEET = """
QWidget {
    /* (font-sans, text-gray-100, text-xs) */
    font-family: 'Inter', 'Malgun Gothic', sans-serif;
    font-size: 10pt; /* (text-xs) React 12px -> 10pt */
    color: #CDD6F4; /* (text-gray-100) */
    background-color: #11111B; /* (bg-gray-900) */
}

/* --- Card (Card.tsx) --- */
#Card {
    background-color: #181825; /* (bg-gray-800) */
    border-radius: 8px; /* (rounded-lg) */
    /* (shadow-xl) QFrame.StyledPanel로 대체 */
}
#CardTitle {
    font-size: 10pt; /* (text-xs) */
    font-weight: bold;
    color: #89B4FA; /* (text-cyan-400) */
    margin-bottom: 4px; /* (mb-1) */
    border-bottom: 1px solid #313244; /* (border-b border-gray-700) */
    padding-bottom: 2px; /* (pb-0.5) */
}

/* --- Header (Header.tsx) --- */
#HeaderFrame {
    background-color: transparent; /* mb-1.5는 main_layout spacing으로 처리 */
}
#HeaderCard {
    background-color: #181825; /* (bg-gray-800) */
    border-radius: 8px; /* (rounded-lg) */
    padding: 6px; /* (p-1.5) */
}
#HeaderLabel {
    font-weight: bold;
    color: #A6ADC8; /* (text-gray-400) */
    font-size: 10pt; /* (text-xs) */
}
#HeaderValueA, #HeaderValueB {
    font-size: 11pt; /* (text-sm) */
    color: #94E2D5; /* (text-green-400) */
}
#HeaderValueTotal {
    font-size: 11pt; /* (text-sm) */
    color: #89DCEB; /* (text-cyan-400) */
}

/* --- Buttons --- */
QPushButton {
    background-color: #313244; /* (bg-gray-700) */
    color: #CDD6F4;
    border: 1px solid #45475A; /* (border-gray-600) */
    border-radius: 5px; /* (rounded) */
    padding: 4px 8px; /* (py-1 px-3) */
    font-size: 10pt; /* (text-xs) */
    font-weight: bold;
}
QPushButton:hover {
    background-color: #45475A; /* (hover:bg-gray-600) */
}
QPushButton:disabled {
    background-color: #585B70; /* (disabled:bg-gray-500) */
    color: #9399B2;
}

/* (RestartButton) */
#BtnRestart {
    background-color: #FAB387; /* (bg-yellow-600) */
    color: #1E1E2E;
}
#BtnRestart:hover { background-color: #F79C66; } /* (hover:bg-yellow-700) */

/* (QuitButton) */
#BtnQuit {
    background-color: #F38BA8; /* (bg-red-600) */
    color: #1E1E2E;
}
#BtnQuit:hover { background-color: #EE6E8E; } /* (hover:bg-red-700) */

/* (StrategyPanel, LeverageControl, ApiSettings) */
#BtnCyan {
    background-color: #89DCEB; /* (bg-cyan-600) */
    color: #1E1E2E;
}
#BtnCyan:hover { background-color: #69C4D3; } /* (hover:bg-cyan-700) */

/* (IndividualOrderPanel) */
#BtnBlue {
    background-color: #89B4FA; /* (bg-blue-600) */
    color: #1E1E2E;
}
#BtnBlue:hover { background-color: #6997DE; } /* (hover:bg-blue-700) */

/* (OpenOrdersPanel) */
#BtnYellow {
    background-color: #FAB387; /* (bg-yellow-600) */
    color: #1E1E2E;
}
#BtnYellow:hover { background-color: #F79C66; } /* (hover:bg-yellow-700) */

#BtnCancel {
    background-color: #F38BA8; /* (bg-red-600) */
    color: #1E1E2E;
    padding: 2px 6px; /* (py-0.5 px-1.5) */
}
#BtnCancel:hover { background-color: #EE6E8E; }

/* (StrategyPanel, IndividualOrderPanel - Toggle Buttons) */
QPushButton:checkable:checked {
    background-color: #89B4FA; /* (bg-cyan-500) */
    color: #1E1E2E;
    border-color: #89B4FA;
}
#BtnLong:checkable:checked {
    background-color: #94E2D5; /* (bg-green-600) */
    color: #1E1E2E;
    border-color: #94E2D5;
}
#BtnShort:checkable:checked {
    background-color: #F38BA8; /* (bg-red-600) */
    color: #1E1E2E;
    border-color: #F38BA8;
}

/* --- Inputs (ApiSettings, StrategyPanel, etc.) --- */
QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {
    background-color: #313244; /* (bg-gray-700) */
    border: 1px solid #45475A; /* (border-gray-600) */
    border-radius: 5px; /* (rounded) */
    padding: 4px; /* (px-2 py-0.5) */
    color: #CDD6F4; /* (text-white) */
    font-size: 10pt; /* (text-xs) */
    min-height: 18px; 
}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus {
    border-color: #89DCEB; /* (focus:ring-cyan-500) */
}
QLineEdit:disabled, QComboBox:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled {
    opacity: 0.5; /* (disabled:opacity-50) */
}

/* (StackedInput) */
#InputLabel {
    color: #A6ADC8; /* (text-gray-400) */
    font-size: 10pt; /* (text-xs) */
    font-weight: bold;
    margin-bottom: -2px; /* (mb-0.5) */
}
#InputDescription {
    color: #7F849C; /* (text-gray-500) */
    font-size: 9pt; /* (text-xs) */
}

/* (QComboBox) */
QComboBox::drop-down { border: 0px; }
QComboBox::down-arrow {
    image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="%23CDD6F4" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M1.646 4.646a.5.5 0 0 1 .708 0L8 10.293l5.646-5.647a.5.5 0 0 1 .708.708l-6 6a.5.5 0 0 1-.708 0l-6-6a.5.5 0 0 1 0-.708z"/></svg>');
    width: 12px; height: 12px; margin-right: 5px;
}
/* (QSpinBox) */
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
QSpinBox::up-button, QSpinBox::down-button {
    border: 0px;
    width: 0px;
}

/* --- Dashboard (Dashboard.tsx) --- */
#DashLabel {
    color: #A6ADC8; /* (text-gray-400) */
    font-weight: bold;
}
#DashValue {
    font-family: 'Consolas', 'Courier New', monospace; /* (font-mono) */
}
#LongIcon, #DashValueLong {
    color: #94E2D5; /* (text-green-400) */
    font-weight: bold;
}
#ShortIcon, #DashValueShort {
    color: #F38BA8; /* (text-red-400) */
    font-weight: bold;
}
#NoneIcon, #DashValueNone {
    color: #A6ADC8; /* (text-gray-400) */
    font-weight: bold;
}
#DashValuePnlPositive { color: #94E2D5; } /* (text-green-400) */
#DashValuePnlNegative { color: #F38BA8; } /* (text-red-400) */
#DashValuePnlZero { color: #A6ADC8; } /* (text-gray-400) */


/* --- OpenOrdersPanel (OpenOrdersPanel.tsx) --- */
QTableWidget {
    background-color: #1E1E2E; /* (bg-gray-800) */
    border: none;
    gridline-color: #313244; /* (border-gray-700) */
}
QHeaderView::section {
    background-color: #1E1E2E;
    color: #A6ADC8; /* (text-gray-400) */
    padding: 4px;
    border: none;
    border-bottom: 1px solid #313244; /* (border-b border-gray-700) */
    font-weight: bold;
}
QTableWidget::item {
    padding: 4px;
    border-bottom: 1px solid #313244;
}
QTableWidget::item:selected {
    background-color: #45475A;
}
#OrderQtyUnfilled { color: #FAB387; } /* (text-yellow-400) */
#OrderPrice { color: #89DCEB; } /* (text-cyan-400) */


/* --- LogPanel (LogPanel.tsx) --- */
#LogPanel {
    background-color: #11111B; /* (bg-gray-900) */
    border: 1px solid #313244;
    border-radius: 5px; /* (rounded-md) */
    font-family: 'Consolas', 'Courier New', monospace; /* (font-mono) */
    font-size: 10pt; /* (text-xs) */
    color: #BAC2DE; /* (text-gray-200) */
}
#LogLevel_INFO { color: #A6ADC8; } /* (text-gray-400) */
#LogLevel_SUCCESS { color: #94E2D5; } /* (text-green-400) */
#LogLevel_WARN { color: #FAB387; } /* (text-yellow-400) */
#LogLevel_ERROR { color: #F38BA8; } /* (text-red-400) */

/* --- ConnectionStatus (ConnectionStatus.tsx - 미사용) --- */
#StatusDot {
    border-radius: 5px; /* (rounded-full) */
    width: 10px;
    height: 10px;
}
#StatusDotConnected { background-color: #94E2D5; } /* (bg-green-500) */
#StatusDotDisconnected { background-color: #F38BA8; } /* (bg-red-500) */

/* --- QSplitter --- */
QSplitter::handle {
    background-color: #313244;
}
QSplitter::handle:horizontal { width: 5px; }
QSplitter::handle:vertical { height: 5px; }
"""

class MainWindow(QMainWindow):
    """
    (React: App.tsx)
    메인 애플리케이션 윈도우.
    React의 'App' 컴포넌트처럼 모든 상태와 UI를 관리합니다.
    """
    
    # --- State (React: useState) ---
    
    # (React: logs)
    logs: List[LogEntry] = []
    
    # (React: apiClients) - 인증된 API 객체 저장소
    api_clients: Dict[ExchangeId, BaseExchangeAPI] = {}
    
    # (React: authenticatedExchanges) - 인증된 거래소 ID 목록
    authenticated_exchanges: List[ExchangeId] = []
    
    # (React: isVerifying) - API 인증 시도 중 상태
    is_verifying: Dict[ExchangeId, bool] = {}
    
    # (React: selectedA, selectedB) - 전략 거래소
    selected_A: Optional[ExchangeId] = None
    selected_B: Optional[ExchangeId] = None
    
    # (React: exchangeStates) - A, B의 계정 상태 (잔고, 포지션 등)
    exchange_states: Dict[ExchangeId, ExchangeState] = {}

    # (React: openOrders) - 모든 거래소의 미체결 주문
    open_orders: List[Order] = []
    
    # (React: prices) - 모든 거래소의 현재가
    prices: Dict[ExchangeId, float] = {}

    # (React: orderSymbol) - 현재 선택된 심볼
    order_symbol: SupportedSymbol = SupportedSymbol.BTC

    # (React: autoBalanceEnabled, autoBalanceInterval)
    auto_balance_enabled: bool = True
    auto_balance_interval: float = 3.0 # (App.tsx 기본값)
    
    # (React: scale)
    scale: int = 100

    # --- Worker Threads ---
    autobalance_worker: Optional[AutoBalanceWorker] = None

    def __init__(self):
        super().__init__()
        
        # --- App Window Settings ---
        self.setWindowTitle("DEX Hedge Terminal (Python Port)")
        self.setGeometry(100, 100, 1400, 900)
        self.settings = QSettings("MyCo", "DEXHedgeApp_v2")
        
        # --- File Logger Setup ---
        self.setup_file_logger()

        # --- Init UI & Load Config ---
        self.init_ui() # UI 위젯 생성
        self.load_settings_and_config() # API 키, 창 크기 등 로드
        self.connect_signals() # 버튼 클릭 등 시그널 연결
        
        self.add_log("트레이딩 터미널이 초기화되었습니다. API 키를 설정하여 거래를 시작하세요.", LogLevel.INFO)


    def setup_file_logger(self):
        logging.basicConfig(
            filename='debug.log',
            filemode='a', 
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            encoding='utf-8'
        )

    def load_settings_and_config(self):
        # 창 크기/위치 복원
        size = self.settings.value("windowSize", QSize(1400, 900))
        position = self.settings.value("windowPosition", QPoint(100, 100))
        self.resize(size)
        self.move(position)
        
        # config.json에서 API 키 로드
        self.add_log(f"Loading config from {CONFIG_FILE}...")
        if os.path.exists(CONFIG_FILE):
            try:
                # (수정) 'cp949' 오류를 막기 위해 UTF-8 인코딩 명시
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.api_config = json.load(f)
                    self.add_log("Config loaded.")
            except Exception as e:
                self.add_log(f"Error loading {CONFIG_FILE}: {e}", LogLevel.ERROR)
                self.api_config = {}
        else:
            self.add_log(f"{CONFIG_FILE} not found. API keys need to be configured.", LogLevel.WARN)
            self.api_config = {}
            
        # (신규) 저장된 API 키로 즉시 인증 시도
        self.authenticate_saved_apis()

    def save_settings(self):
        # 창 크기/위치 저장
        self.settings.setValue("windowSize", self.size())
        self.settings.setValue("windowPosition", self.pos())
        
        # API 키 config.json에 저장
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f: # (수정) 쓰기에도 UTF-8 적용
                json.dump(self.api_config, f, indent=4)
            self.add_log(f"Saved API configuration to {CONFIG_FILE}", LogLevel.INFO)
        except Exception as e:
            self.add_log(f"Error saving {CONFIG_FILE}: {e}", LogLevel.ERROR)

    def closeEvent(self, event):
        self.add_log("Closing application...")
        self.stop_all_workers()
        self.save_settings() # (API 키도 여기서 저장됨)
        self.add_log("Goodbye.")
        logging.info("--- Application Closed ---")
        event.accept()

    # --- 1. UI Initialization (React Layout -> PySide6) ---
    
    def init_ui(self):
        """React 'App.tsx' 레이아웃을 PySide6 위젯으로 생성합니다."""
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # (React: <div className="flex flex-col h-screen p-1.5 ...">)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5) # (p-1.5)
        main_layout.setSpacing(5) # (gap-1.5)

        # --- 1.1. Header (Header.tsx) ---
        self.header_frame = self.create_header_panel()
        main_layout.addWidget(self.header_frame)

        # --- 1.2. Main Content (React: <main className="flex flex-row ...">) ---
        # QSplitter로 3단 레이아웃 구현
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter, 1) # (flex-grow)

        # --- 2. Left Column (React: "w-1/4 flex flex-col gap-1.5") ---
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(5) # (gap-1.5)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.symbol_selector_card = self.create_symbol_selector_panel()
        self.api_settings_card = self.create_api_settings_panel()
        self.strategy_selector_card = self.create_strategy_selector_panel()
        self.autobalance_card = self.create_autobalance_panel()
        
        left_layout.addWidget(self.symbol_selector_card)
        left_layout.addWidget(self.api_settings_card, 1) # (flex-grow)
        left_layout.addWidget(self.strategy_selector_card)
        left_layout.addWidget(self.autobalance_card)
        
        main_splitter.addWidget(left_panel)
        
        # --- 3. Center Column (React: "w-2/4 flex flex-col gap-1.5") ---
        center_panel = QFrame()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setSpacing(5) # (gap-1.5)
        center_layout.setContentsMargins(0, 0, 0, 0)

        # 3.1. Dashboards (Row 1: grid grid-cols-2 gap-1.5)
        dash_layout = QHBoxLayout()
        dash_layout.setSpacing(5) # (gap-1.5)
        self.dashboard_A = self.create_dashboard_panel(ExchangeId.PACIFICA) # (임시)
        self.dashboard_B = self.create_dashboard_panel(ExchangeId.LIGHTER) # (임시)
        dash_layout.addWidget(self.dashboard_A)
        dash_layout.addWidget(self.dashboard_B)
        center_layout.addLayout(dash_layout)

        # 3.2. Strategy & Leverage (Row 2: grid grid-cols-2 gap-1.5)
        strategy_leverage_layout = QHBoxLayout()
        strategy_leverage_layout.setSpacing(5) # (gap-1.5)
        self.strategy_panel = self.create_strategy_panel()
        self.leverage_panel = self.create_leverage_panel()
        strategy_leverage_layout.addWidget(self.strategy_panel)
        strategy_leverage_layout.addWidget(self.leverage_panel)
        center_layout.addLayout(strategy_leverage_layout)

        # 3.3. Individual Orders (Row 3: flex-grow grid grid-cols-2 gap-1.5)
        individual_order_layout = QHBoxLayout()
        individual_order_layout.setSpacing(5) # (gap-1.5)
        self.individual_order_A = self.create_individual_order_panel(ExchangeId.PACIFICA) # (임시)
        self.individual_order_B = self.create_individual_order_panel(ExchangeId.LIGHTER) # (임시)
        individual_order_layout.addWidget(self.individual_order_A)
        individual_order_layout.addWidget(self.individual_order_B)
        center_layout.addLayout(individual_order_layout, 1) # (flex-grow)

        main_splitter.addWidget(center_panel)

        # --- 4. Right Column (React: "w-1/4 flex flex-col gap-1.5") ---
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(5) # (gap-1.5)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.open_orders_panel = self.create_open_orders_panel()
        self.log_panel = self.create_log_panel()
        
        right_layout.addWidget(self.open_orders_panel, 1) # (flex-1)
        right_layout.addWidget(self.log_panel, 1) # (flex-1)
        
        main_splitter.addWidget(right_panel)
        
        # --- Finalize Layout & Style ---
        main_splitter.setSizes([350, 700, 350]) # (w-1/4, w-2/4, w-1/4)

        self.setStyleSheet(STYLESHEET)


    # --- 1.1. create_header_panel (Header.tsx) ---
    def create_header_panel(self):
        frame = QFrame()
        frame.setObjectName("HeaderFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5) # (gap-1.5)

        # Card 1: Price A
        card_a = QFrame()
        card_a.setObjectName("HeaderCard")
        layout_a = QHBoxLayout(card_a)
        layout_a.addWidget(QLabel("현재가 (A)"), 0, Qt.AlignmentFlag.AlignLeft)
        self.header_price_A = QLabel("$N/A")
        self.header_price_A.setObjectName("HeaderValueA")
        layout_a.addWidget(self.header_price_A, 0, Qt.AlignmentFlag.AlignRight)
        
        # Card 2: Price B
        card_b = QFrame()
        card_b.setObjectName("HeaderCard")
        layout_b = QHBoxLayout(card_b)
        layout_b.addWidget(QLabel("현재가 (B)"), 0, Qt.AlignmentFlag.AlignLeft)
        self.header_price_B = QLabel("$N/A")
        self.header_price_B.setObjectName("HeaderValueB")
        layout_b.addWidget(self.header_price_B, 0, Qt.AlignmentFlag.AlignRight)

        # Card 3: Total Assets
        card_total = QFrame()
        card_total.setObjectName("HeaderCard")
        layout_total = QHBoxLayout(card_total)
        layout_total.addWidget(QLabel("총 자산"), 0, Qt.AlignmentFlag.AlignLeft)
        self.header_total_assets = QLabel("$0.00")
        self.header_total_assets.setObjectName("HeaderValueTotal")
        layout_total.addWidget(self.header_total_assets, 0, Qt.AlignmentFlag.AlignRight)

        # Card 4: Controls
        card_controls = QFrame()
        card_controls.setObjectName("HeaderCard")
        layout_controls = QHBoxLayout(card_controls)
        layout_controls.setSpacing(8) # (gap-2)
        
        self.loading_indicator = LoadingIndicator() # (Python-only)
        
        # (ScaleControl.tsx) - 기능 미구현
        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.setFixedSize(28, 28)
        self.label_zoom = QLabel(" 100% ")
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedSize(28, 28)

        self.btn_restart = QPushButton("재시작")
        self.btn_restart.setObjectName("BtnRestart")
        self.btn_quit = QPushButton("종료")
        self.btn_quit.setObjectName("BtnQuit")
        
        layout_controls.addWidget(self.loading_indicator)
        layout_controls.addStretch()
        layout_controls.addWidget(self.btn_zoom_out)
        layout_controls.addWidget(self.label_zoom)
        layout_controls.addWidget(self.btn_zoom_in)
        layout_controls.addSpacing(10)
        layout_controls.addWidget(self.btn_restart)
        layout_controls.addWidget(self.btn_quit)

        layout.addWidget(card_a, 1)
        layout.addWidget(card_b, 1)
        layout.addWidget(card_total, 1)
        layout.addWidget(card_controls, 1)
        
        return frame

    # --- 2.1. create_symbol_selector_panel (SymbolSelector.tsx) ---
    def create_symbol_selector_panel(self):
        card = Card("거래 설정")
        layout = card.content_layout # (수정)
        
        layout.addWidget(QLabel("거래 심볼"))
        self.combo_symbol = QComboBox()
        # (types.ts: SUPPORTED_SYMBOLS)
        for symbol in SUPPORTED_SYMBOLS:
            self.combo_symbol.addItem(f"{symbol.value}-PERP", symbol) # (text, data)
        
        layout.addWidget(self.combo_symbol)
        return card

    # --- 2.2. create_api_settings_panel (ApiSettings.tsx) ---
    def create_api_settings_panel(self):
        card = Card("API 및 거래소 설정")
        layout = card.content_layout # (수정)
        layout.setSpacing(8) # (space-y-1.5)

        # 1. 거래소 선택 콤보박스
        layout.addWidget(QLabel("거래소"))
        self.combo_api_exchange = QComboBox()
        for ex_id, name in EXCHANGE_NAMES.items():
            self.combo_api_exchange.addItem(name, ex_id) # (text, data)
        layout.addWidget(self.combo_api_exchange)

        # 2. API 입력창 (StackedInput)
        self.api_input_key = StackedInput("API 키", "Pacifica 대시보드에서 발급")
        self.api_input_secret = StackedInput("비밀 키 (Base58)", "Ed25519 지갑 비밀 키", is_password=True)
        self.api_input_address = StackedInput("지갑 주소", "Base58 인코딩된 주소")
        # (Lighter 전용 - 숨김/표시 처리 필요)
        self.api_input_account_id = StackedInput("계정 ID", "예: 0")
        self.api_input_l1_address = StackedInput("L1 주소 (EVM)", "0x로 시작하는 EVM 주소")
        
        layout.addLayout(self.api_input_key)
        layout.addLayout(self.api_input_secret)
        layout.addLayout(self.api_input_address)
        layout.addLayout(self.api_input_account_id)
        layout.addLayout(self.api_input_l1_address)
        
        # (Lighter 입력창은 기본적으로 숨김)
        self.api_input_account_id.label.hide()
        self.api_input_account_id.input.hide()
        self.api_input_account_id.description.hide()
        self.api_input_l1_address.label.hide()
        self.api_input_l1_address.input.hide()
        self.api_input_l1_address.description.hide()

        # 3. 저장 버튼
        self.btn_api_save = QPushButton("저장 및 인증")
        self.btn_api_save.setObjectName("BtnCyan")
        layout.addWidget(self.btn_api_save)
        
        # 4. 인증된 거래소 리스트
        layout.addWidget(QLabel("인증된 거래소:"))
        self.list_auth_exchanges = QListWidget()
        self.list_auth_exchanges.addItem("없음")
        self.list_auth_exchanges.setFixedHeight(60) # 임시
        layout.addWidget(self.list_auth_exchanges, 1) # (flex-grow)
        
        return card

    # --- 2.3. create_strategy_selector_panel (StrategySelector.tsx) ---
    def create_strategy_selector_panel(self):
        card = Card("전략 거래소 선택")
        layout = card.content_layout # (수정)
        
        layout.addWidget(QLabel("A 거래소 (지정가)"))
        self.combo_strategy_A = QComboBox()
        self.combo_strategy_A.addItem("-- 선택 --", None)
        layout.addWidget(self.combo_strategy_A)

        layout.addWidget(QLabel("B 거래소 (시장가)"))
        self.combo_strategy_B = QComboBox()
        self.combo_strategy_B.addItem("-- 선택 --", None)
        layout.addWidget(self.combo_strategy_B)
        
        return card

    # --- 2.4. create_autobalance_panel (AutoBalancePanel.tsx) ---
    def create_autobalance_panel(self):
        card = Card("포지션 자동 균형")
        layout = card.content_layout # (수정)

        # 1. 토글
        toggle_frame = QFrame()
        toggle_frame.setObjectName("ToggleFrame") # (bg-gray-700)
        toggle_layout = QHBoxLayout(toggle_frame)
        
        toggle_text_layout = QVBoxLayout()
        toggle_text_layout.addWidget(QLabel("자동 균형 활성화"))
        toggle_text_layout.addWidget(QLabel("A를 기준으로 포지션 불일치를 자동 보정합니다."))
        
        self.toggle_autobalance = ToggleSwitch()
        self.toggle_autobalance.setChecked(self.auto_balance_enabled)
        
        toggle_layout.addLayout(toggle_text_layout, 1)
        toggle_layout.addWidget(self.toggle_autobalance)
        layout.addWidget(toggle_frame)
        
        # 2. 감시 주기
        self.input_autobalance_interval = LabeledInput(
            "감시 주기 (초):", 
            str(self.auto_balance_interval),
            input_type='float' # (React: step=0.1)
        )
        layout.addLayout(self.input_autobalance_interval)

        return card

    # --- 3.1. create_dashboard_panel (Dashboard.tsx) ---
    def create_dashboard_panel(self, ex_id: ExchangeId):
        card = Card(f"{EXCHANGE_NAMES[ex_id]} (미선택)")
        card.setObjectName(f"Dashboard_{ex_id.value}") # 식별자
        layout = card.content_layout # (수정)
        layout.setSpacing(4) # (space-y-1)
        
        # Grid 레이아웃 (Label, Value)
        grid = QGridLayout()
        grid.setSpacing(4)
        
        # 1. 포지션
        grid.addWidget(QLabel("📘 포지션"), 0, 0)
        self.dash_pos = IconLabel('none')
        self.dash_pos.setObjectName("DashValueNone")
        grid.addWidget(self.dash_pos, 0, 1, Qt.AlignmentFlag.AlignRight)

        # 2. 수량
        grid.addWidget(QLabel("🔢 수량"), 1, 0)
        self.dash_qty = QLabel("0.00000")
        self.dash_qty.setObjectName("DashValue")
        grid.addWidget(self.dash_qty, 1, 1, Qt.AlignmentFlag.AlignRight)

        # 3. 평단가
        self.dash_entry_label = QLabel("📈 평단가")
        grid.addWidget(self.dash_entry_label, 2, 0)
        self.dash_entry = QLabel("$0.00")
        self.dash_entry.setObjectName("DashValue")
        grid.addWidget(self.dash_entry, 2, 1, Qt.AlignmentFlag.AlignRight)

        # 4. 레버리지
        grid.addWidget(QLabel("⚖️ 레버리지"), 3, 0)
        self.dash_leverage = QLabel("N/Ax")
        self.dash_leverage.setObjectName("DashValue")
        grid.addWidget(self.dash_leverage, 3, 1, Qt.AlignmentFlag.AlignRight)

        # 5. 손익 (PnL)
        grid.addWidget(QLabel("💰 손익"), 4, 0)
        self.dash_pnl = QLabel("0.00")
        self.dash_pnl.setObjectName("DashValuePnlZero")
        grid.addWidget(self.dash_pnl, 4, 1, Qt.AlignmentFlag.AlignRight)

        # 6. 잔고
        grid.addWidget(QLabel("💵 잔고"), 5, 0)
        self.dash_balance = QLabel("0.00 USDC")
        self.dash_balance.setObjectName("DashValue")
        grid.addWidget(self.dash_balance, 5, 1, Qt.AlignmentFlag.AlignRight)
        
        layout.addLayout(grid)
        layout.addStretch() # (flex-col justify-between h-full)
        
        # 나중에 쉽게 접근할 수 있도록 위젯들을 저장
        setattr(self, f"dash_card_{ex_id.value}", card)
        setattr(self, f"dash_pos_{ex_id.value}", self.dash_pos)
        setattr(self, f"dash_qty_{ex_id.value}", self.dash_qty)
        setattr(self, f"dash_entry_label_{ex_id.value}", self.dash_entry_label)
        setattr(self, f"dash_entry_{ex_id.value}", self.dash_entry)
        setattr(self, f"dash_leverage_{ex_id.value}", self.dash_leverage)
        setattr(self, f"dash_pnl_{ex_id.value}", self.dash_pnl)
        setattr(self, f"dash_balance_{ex_id.value}", self.dash_balance)

        return card

    # --- 3.2. create_strategy_panel (StrategyPanel.tsx) ---
    def create_strategy_panel(self):
        card = Card("전략 주문")
        layout = card.content_layout # (수정)
        layout.setSpacing(8) # (space-y-2)

        # 1. 총 수량
        self.input_strategy_qty = LabeledInput("총 수량 (Q):", "0.1", input_type='float')
        layout.addLayout(self.input_strategy_qty)
        
        # 2. 오프셋
        self.label_strategy_offset = QLabel(f"A 거래소 지정가 오프셋 (현재가: 0.00)")
        self.spin_strategy_offset = QDoubleSpinBox()
        self.spin_strategy_offset.setRange(-9999.99, 9999.99)
        self.spin_strategy_offset.setDecimals(2)
        self.spin_strategy_offset.setValue(0.5)
        layout.addWidget(self.label_strategy_offset)
        layout.addWidget(self.spin_strategy_offset)

        # 3. 방향 선택
        layout.addWidget(QLabel("방향 선택"))
        strategy_dir_layout = QHBoxLayout()
        self.btn_strategy_A_Long = QPushButton("(A) 롱 → (B) 숏")
        self.btn_strategy_A_Short = QPushButton("(A) 숏 → (B) 롱")
        self.btn_strategy_A_Long.setCheckable(True)
        self.btn_strategy_A_Short.setCheckable(True)
        self.btn_strategy_A_Long.setObjectName("BtnLong")
        self.btn_strategy_A_Short.setObjectName("BtnShort")
        strategy_dir_layout.addWidget(self.btn_strategy_A_Long)
        strategy_dir_layout.addWidget(self.btn_strategy_A_Short)
        layout.addLayout(strategy_dir_layout)
        
        layout.addStretch() # (mt-auto)
        
        # 4. 실행 버튼
        self.btn_strategy_start = QPushButton("주문 실행")
        self.btn_strategy_start.setObjectName("BtnBlue")
        layout.addWidget(self.btn_strategy_start)
        
        # (신규) 전략 중지 버튼 (Python 고유 기능, QThread 중지용)
        self.btn_strategy_stop = QPushButton("전략 중지")
        self.btn_strategy_stop.setEnabled(False) # 기본 비활성화
        layout.addWidget(self.btn_strategy_stop)

        return card

    # --- 3.2. create_leverage_panel (LeverageControl.tsx) ---
    def create_leverage_panel(self):
        card = Card("레버리지 설정")
        layout = card.content_layout # (수정)
        
        # 1. 거래소 선택
        layout.addWidget(QLabel("거래소 선택"))
        self.combo_leverage_exchange = QComboBox()
        self.combo_leverage_exchange.addItem("-- 인증된 거래소 없음 --", None)
        layout.addWidget(self.combo_leverage_exchange)

        # 2. 레버리지 입력
        self.label_leverage = QLabel("레버리지 (현재: N/Ax)")
        self.spin_leverage = QSpinBox()
        self.spin_leverage.setRange(1, 100)
        self.spin_leverage.setValue(10)
        layout.addWidget(self.label_leverage)
        layout.addWidget(self.spin_leverage)
        
        layout.addStretch() # (mt-auto)

        # 3. 설정 버튼
        self.btn_leverage_set = QPushButton("설정")
        self.btn_leverage_set.setObjectName("BtnCyan")
        layout.addWidget(self.btn_leverage_set)
        
        return card

    # --- 3.3. create_individual_order_panel (IndividualOrderPanel.tsx) ---
    def create_individual_order_panel(self, ex_id: ExchangeId):
        card = Card(f"{EXCHANGE_NAMES[ex_id]} (미선택)")
        card.setObjectName(f"IndividualOrder_{ex_id.value}") # 식별자
        layout = card.content_layout # (수정)
        
        # 1. 타입 (시장가/지정가)
        type_layout = QHBoxLayout()
        btn_mkt = QPushButton("시장가")
        btn_lmt = QPushButton("지정가")
        btn_mkt.setCheckable(True)
        btn_lmt.setCheckable(True)
        btn_mkt.setChecked(True)
        type_layout.addWidget(btn_mkt, 1)
        type_layout.addWidget(btn_lmt, 1)
        
        # 2. 방향 (롱/숏)
        side_layout = QHBoxLayout()
        btn_long = QPushButton("롱")
        btn_short = QPushButton("숏")
        btn_long.setCheckable(True)
        btn_short.setCheckable(True)
        btn_long.setChecked(True)
        btn_long.setObjectName("BtnLong")
        btn_short.setObjectName("BtnShort")
        side_layout.addWidget(btn_long, 1)
        side_layout.addWidget(btn_short, 1)
        
        # 3. 수량
        qty_layout = QHBoxLayout()
        spin_qty = QDoubleSpinBox()
        spin_qty.setRange(0, 999999.99)
        spin_qty.setDecimals(6)
        # (수정 1/2)
        spin_qty.lineEdit().setPlaceholderText("수량 (Q)")
        
        btn_max_qty = QPushButton("MAX")
        btn_max_qty.setFixedWidth(50)
        qty_layout.addWidget(spin_qty, 1)
        qty_layout.addWidget(btn_max_qty)

        # 4. 오프셋 (지정가용)
        spin_offset = QDoubleSpinBox()
        spin_offset.setRange(-9999.99, 9999.99)
        spin_offset.setDecimals(2)
        spin_offset.setValue(0.5)
        # (수정 2/2)
        spin_offset.lineEdit().setPlaceholderText("오프셋 (현재가: 0.00)")
        spin_offset.setEnabled(False) # MKT가 기본

        # 5. 실행 버튼
        btn_exec = QPushButton("주문 실행")
        btn_exec.setObjectName("BtnBlue")
        
        layout.addLayout(type_layout)
        layout.addLayout(side_layout)
        layout.addLayout(qty_layout)
        layout.addWidget(spin_offset)
        layout.addStretch() # (mt-auto)
        layout.addWidget(btn_exec)

        # 위젯 저장 (새 이름 사용)
        setattr(self, f"btn_ind_{ex_id.value}_mkt", btn_mkt)
        setattr(self, f"btn_ind_{ex_id.value}_lmt", btn_lmt)
        setattr(self, f"btn_ind_{ex_id.value}_long", btn_long)
        setattr(self, f"btn_ind_{ex_id.value}_short", btn_short)
        setattr(self, f"spin_ind_{ex_id.value}_qty", spin_qty)
        setattr(self, f"spin_ind_{ex_id.value}_offset", spin_offset)
        setattr(self, f"btn_ind_{ex_id.value}_exec", btn_exec)
        setattr(self, f"btn_ind_{ex_id.value}_max", btn_max_qty)

        # 시그널 연결
        btn_lmt.toggled.connect(spin_offset.setEnabled)
        
        return card

    # --- 4.1. create_open_orders_panel (OpenOrdersPanel.tsx) ---
    def create_open_orders_panel(self):
        # (React: Card title={panelTitle})
        card = Card("미체결 주문")
        layout = card.content_layout # (수정)
        
        # 1. '전체 취소' 버튼을 타이틀바에 추가
        self.btn_cancel_all_orders = QPushButton("전체 취소")
        self.btn_cancel_all_orders.setObjectName("BtnYellow")
        # (Card의 main_layout(VBox)의 0번째(title_label)를 찾아서 HBox로 교체)
        title_layout = QHBoxLayout()
        title_layout.addWidget(card.title_label, 1)
        title_layout.addWidget(self.btn_cancel_all_orders)
        # (기존 QVBoxLayout의 0번째 항목을 HBox 레이아웃으로 교체)
        card.main_layout.insertLayout(0, title_layout)
        card.main_layout.removeWidget(card.title_label) # 원본 라벨 제거
        card.title_label.deleteLater() # (메모리 정리)

        # 2. 테이블
        self.table_open_orders = QTableWidget()
        self.table_open_orders.setColumnCount(6)
        self.table_open_orders.setHorizontalHeaderLabels(["거래소", "방향", "총수량", "미체결", "가격", ""]) # 취소 버튼
        
        header = self.table_open_orders.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents) # 취소 버튼
        
        self.table_open_orders.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_open_orders.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_open_orders.verticalHeader().hide()
        
        layout.addWidget(self.table_open_orders, 1) # (flex-1)
        
        return card

    # --- 4.2. create_log_panel (LogPanel.tsx) ---
    def create_log_panel(self):
        card = Card("시스템 로그")
        layout = card.content_layout # (수정)
        
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setObjectName("LogPanel") # 스타일 적용
        
        layout.addWidget(self.log_widget, 1) # (flex-1)
        return card


    # --- 2. Signal Connection (React: onClick={...}) ---

    def connect_signals(self):
        """UI 위젯의 시그널을 슬롯(핸들러)에 연결합니다."""
        
        # --- Header ---
        self.btn_quit.clicked.connect(self.quit_app)
        self.btn_restart.clicked.connect(self.not_implemented)
        self.btn_zoom_in.clicked.connect(self.not_implemented)
        self.btn_zoom_out.clicked.connect(self.not_implemented)

        # --- Left Panel ---
        self.combo_symbol.currentTextChanged.connect(self.on_symbol_changed)
        self.combo_api_exchange.currentTextChanged.connect(self.on_api_combo_changed)
        self.btn_api_save.clicked.connect(self.on_save_api_creds)
        self.combo_strategy_A.currentTextChanged.connect(self.on_strategy_exchange_changed)
        self.combo_strategy_B.currentTextChanged.connect(self.on_strategy_exchange_changed)
        self.toggle_autobalance.toggled.connect(self.on_autobalance_toggled)
        self.input_autobalance_interval.input.valueChanged.connect(self.on_autobalance_interval_changed)

        # --- Center Panel ---
        # (Strategy)
        self.btn_strategy_A_Long.clicked.connect(lambda: self.set_button_group(self.btn_strategy_A_Short, False))
        self.btn_strategy_A_Short.clicked.connect(lambda: self.set_button_group(self.btn_strategy_A_Long, False))
        self.btn_strategy_start.clicked.connect(self.on_execute_strategy_order)
        self.btn_strategy_stop.clicked.connect(self.on_stop_strategy) # (Python-only)
        # (Leverage)
        self.btn_leverage_set.clicked.connect(self.on_set_leverage)
        self.combo_leverage_exchange.currentTextChanged.connect(self.on_leverage_combo_changed)
        
        # --- Right Panel ---
        # (수정) 'cellClicked'를 버튼이 아닌 테이블에 연결
        self.btn_cancel_all_orders.clicked.connect(self.on_cancel_all_orders)
        self.table_open_orders.cellClicked.connect(self.on_order_cancel_clicked)
        
        # --- Individual Orders (A, B) ---
        # (A)
        ex_id_a = ExchangeId.PACIFICA # (임시 ID, 나중에 동적으로)
        getattr(self, f"btn_ind_{ex_id_a.value}_mkt").clicked.connect(lambda: self.set_button_group(getattr(self, f"btn_ind_{ex_id_a.value}_lmt"), False))
        getattr(self, f"btn_ind_{ex_id_a.value}_lmt").clicked.connect(lambda: self.set_button_group(getattr(self, f"btn_ind_{ex_id_a.value}_mkt"), False))
        getattr(self, f"btn_ind_{ex_id_a.value}_long").clicked.connect(lambda: self.set_button_group(getattr(self, f"btn_ind_{ex_id_a.value}_short"), False))
        getattr(self, f"btn_ind_{ex_id_a.value}_short").clicked.connect(lambda: self.set_button_group(getattr(self, f"btn_ind_{ex_id_a.value}_long"), False))
        getattr(self, f"btn_ind_{ex_id_a.value}_exec").clicked.connect(self.on_execute_individual_order_A)
        getattr(self, f"btn_ind_{ex_id_a.value}_max").clicked.connect(self.on_individual_max_A)
        
        # (B)
        ex_id_b = ExchangeId.LIGHTER # (임시 ID, 나중에 동적으로)
        getattr(self, f"btn_ind_{ex_id_b.value}_mkt").clicked.connect(lambda: self.set_button_group(getattr(self, f"btn_ind_{ex_id_b.value}_lmt"), False))
        getattr(self, f"btn_ind_{ex_id_b.value}_lmt").clicked.connect(lambda: self.set_button_group(getattr(self, f"btn_ind_{ex_id_b.value}_mkt"), False))
        getattr(self, f"btn_ind_{ex_id_b.value}_long").clicked.connect(lambda: self.set_button_group(getattr(self, f"btn_ind_{ex_id_b.value}_short"), False))
        getattr(self, f"btn_ind_{ex_id_b.value}_short").clicked.connect(lambda: self.set_button_group(getattr(self, f"btn_ind_{ex_id_b.value}_long"), False))
        getattr(self, f"btn_ind_{ex_id_b.value}_exec").clicked.connect(self.on_execute_individual_order_B)
        getattr(self, f"btn_ind_{ex_id_b.value}_max").clicked.connect(self.on_individual_max_B)


    # --- 3. API Handlers (React: handle... functions) ---

    @Slot()
    def authenticate_saved_apis(self):
        """(신규) config.json에 저장된 모든 API 키로 인증을 시도합니다."""
        self.add_log("Authenticating saved API credentials...", LogLevel.INFO)
        
        for ex_name, creds_dict in self.api_config.items():
            if creds_dict.get('apiKey') and creds_dict.get('apiSecret'):
                try:
                    ex_id = EXCHANGE_ID_MAP.get(ex_name)
                    if not ex_id:
                        self.add_log(f"Unknown exchange in config.json: {ex_name}", LogLevel.WARN)
                        continue
                        
                    creds = ApiCredentials(
                        apiKey=creds_dict['apiKey'],
                        apiSecret=creds_dict['apiSecret'],
                        accountAddress=creds_dict.get('accountAddress'),
                        accountId=creds_dict.get('accountId'),
                        l1Address=creds_dict.get('l1Address')
                    )
                    
                    # (React: handleSaveApiCreds 로직 재사용)
                    self.handle_api_auth(ex_id, creds)
                    
                except Exception as e:
                    self.add_log(f"Failed to auto-auth {ex_name}: {e}", LogLevel.ERROR)

    @Slot()
    def on_save_api_creds(self):
        """
        (React: handleSaveApiCreds)
        '저장 및 인증' 버튼 클릭 시 호출됩니다.
        """
        ex_id: ExchangeId = self.combo_api_exchange.currentData()
        
        creds = ApiCredentials(
            apiKey=self.api_input_key.input.text(),
            apiSecret=self.api_input_secret.input.text(),
            accountAddress=self.api_input_address.input.text() if ex_id == ExchangeId.PACIFICA else None,
            accountId=int(self.api_input_account_id.input.text()) if ex_id == ExchangeId.LIGHTER and self.api_input_account_id.input.text() else None,
            l1Address=self.api_input_l1_address.input.text() if ex_id == ExchangeId.LIGHTER else None
        )

        # (React: isPacificaSaveDisabled, isLighterSaveDisabled)
        if not creds.apiKey or not creds.apiSecret:
             self.add_log(f"[{EXCHANGE_NAMES[ex_id]}] API 키와 비밀 키를 입력하세요.", LogLevel.WARN)
             return
        if ex_id == ExchangeId.PACIFICA and not creds.accountAddress:
             self.add_log(f"[{EXCHANGE_NAMES[ex_id]}] 지갑 주소를 입력하세요.", LogLevel.WARN)
             return
        if ex_id == ExchangeId.LIGHTER and (creds.accountId is None or not creds.l1Address):
             self.add_log(f"[{EXCHANGE_NAMES[ex_id]}] 계정 ID와 L1 주소를 입력하세요.", LogLevel.WARN)
             return

        # (React: App.tsx의 handleSaveApiCreds)
        self.handle_api_auth(ex_id, creds)
        
        # (React: setCreds({})) - 입력창 비우기
        self.api_input_key.input.clear()
        self.api_input_secret.input.clear()
        self.api_input_address.input.clear()
        self.api_input_account_id.input.clear()
        self.api_input_l1_address.input.clear()
        
        # 설정 파일에 즉시 저장
        self.api_config[EXCHANGE_NAMES[ex_id]] = creds.__dict__
        self.save_settings()


    def handle_api_auth(self, ex_id: ExchangeId, creds: ApiCredentials):
        """(React: handleSaveApiCreds) - 공통 인증 로직"""
        ex_name = EXCHANGE_NAMES[ex_id]
        self.add_log(f"[{ex_name}] API 클라이언트 생성 및 인증 시도...", LogLevel.INFO)
        
        self.is_verifying[ex_id] = True
        self.update_api_settings_ui() # (인증 중... 버튼)

        try:
            # 1. API 클라이언트 생성
            if ex_id not in self.api_clients:
                ApiClass = EXCHANGE_MAP[ex_id]
                client = ApiClass(name=ex_name)
                
                # (중요) API 시그널을 메인 윈도우 슬롯에 연결
                client.log_message.connect(self.add_log)
                client.state_update.connect(self.on_state_update)
                client.orders_update.connect(self.on_orders_update)
                client.price_update.connect(self.on_price_update)
                
                self.api_clients[ex_id] = client
            else:
                client = self.api_clients[ex_id]

            # 2. 연결 (API 키 인증)
            if client.connect(creds):
                # (React: setAuthenticatedExchanges)
                if ex_id not in self.authenticated_exchanges:
                    self.authenticated_exchanges.append(ex_id)
                
                self.add_log(f"[{ex_name}] API 인증 성공.", LogLevel.SUCCESS)
                
                # (React: useEffect[apiClients])
                client.start_streaming(self.order_symbol)
                
            else:
                self.add_log(f"[{ex_name}] API 인증 실패: (연결 오류)", LogLevel.ERROR)

        except Exception as e:
            self.add_log(f"[{ex_name}] API 인증 실패: {e}", LogLevel.ERROR)
            if ex_id in self.api_clients:
                del self.api_clients[ex_id] # 실패한 클라이언트 제거
        
        self.is_verifying[ex_id] = False
        self.update_api_settings_ui() # UI 갱신 (인증된 목록, 콤보박스)
        self.update_strategy_selector_ui()
        self.update_leverage_panel_ui()

    # --- 5. UI Slots & Callbacks --- (수정: 4 -> 5)

    @Slot()
    def quit_app(self):
        """(React: QuitButton) 헤더의 '종료' 버튼 클릭 시 앱을 종료합니다."""
        self.add_log("Quit requested.")
        self.close()
        
    @Slot(str)
    def on_symbol_changed(self, text: str):
        """
        (React: setOrderSymbol)
        '거래 심볼' 콤보박스 변경 시 호출됩니다.
        """
        new_symbol: SupportedSymbol = self.combo_symbol.currentData()
        if new_symbol == self.order_symbol:
            return
            
        self.order_symbol = new_symbol
        self.add_log(f"거래 심볼이 {new_symbol.value}-PERP로 변경되었습니다.", LogLevel.INFO)
        
        # (React: useEffect[orderSymbol])
        # 모든 활성 API 클라이언트의 스트리밍 재시작
        for ex_id, client in self.api_clients.items():
            client.stop_streaming()
            client.start_streaming(self.order_symbol)
            
        # (신규) 상태 초기화
        self.open_orders = []
        self.exchange_states = {}
        self.update_all_dashboards()
        self.update_open_orders_table()

    @Slot(str)
    def on_strategy_exchange_changed(self, text: str):
        """
        (React: setSelectedA, setSelectedB)
        '전략 거래소' (A, B) 콤보박스 변경 시 호출됩니다.
        """
        combo = self.sender()
        selected_id: Optional[ExchangeId] = combo.currentData() # (None or ExchangeId)
        
        if combo == self.combo_strategy_A:
            if selected_id == self.selected_B and selected_id is not None:
                self.add_log("A와 B는 서로 다른 거래소여야 합니다.", LogLevel.WARN)
                self.combo_strategy_A.setCurrentIndex(0) # "-- 선택 --"
                self.selected_A = None
                return
            self.selected_A = selected_id
            self.add_log(f"전략 A 거래소: {text}", LogLevel.INFO)
        else: # combo_strategy_B
            if selected_id == self.selected_A and selected_id is not None:
                self.add_log("A와 B는 서로 다른 거래소여야 합니다.", LogLevel.WARN)
                self.combo_strategy_B.setCurrentIndex(0)
                self.selected_B = None
                return
            self.selected_B = selected_id
            self.add_log(f"전략 B 거래소: {text}", LogLevel.INFO)
            
        # 선택 변경 시, 대시보드와 개별 주문 패널의 타겟을 즉시 업데이트
        self.update_dashboard_targets()
        self.update_individual_order_targets()
        self.update_strategy_selector_ui() # (A, B가 서로를 필터링하도록)
        self.update_autobalance_worker() # (워커 설정 업데이트)

    @Slot(bool)
    def on_autobalance_toggled(self, checked: bool):
        """
        (React: setAutoBalanceEnabled)
        '자동 균형' 토글 시 호출됩니다.
        """
        self.auto_balance_enabled = checked
        self.input_autobalance_interval.input.setEnabled(checked)
        self.update_autobalance_worker() # (워커 시작/중지)
    
    @Slot(float)
    def on_autobalance_interval_changed(self, value: float):
        """
        (React: setAutoBalanceInterval)
        '감시 주기' 변경 시 호출됩니다.
        """
        self.auto_balance_interval = value
        self.update_autobalance_worker() # (워커 설정 업데이트)

    def update_autobalance_worker(self):
        """
        (React: checkAutoBalance)
        자동 균형 스레드(Worker)를 시작/중지/설정합니다.
        """
        if self.auto_balance_enabled and self.selected_A and self.selected_B:
            api_a = self.api_clients.get(self.selected_A)
            api_b = self.api_clients.get(self.selected_B)
            
            if not api_a or not api_b:
                self.add_log("[AutoBalance] A, B API가 모두 인증되지 않았습니다.", LogLevel.WARN)
                self.toggle_autobalance.setChecked(False) # 토글 강제 해제
                return

            if not self.autobalance_worker:
                # (스레드 생성)
                self.autobalance_worker = AutoBalanceWorker()
                self.autobalance_worker.log_message.connect(self.add_log)
                # (중요) 메인 스레드의 최신 상태를 워커로 전송
                self.signal_state_updated_for_worker.connect(self.autobalance_worker.update_states)
            
            # (스레드 설정 및 시작)
            self.autobalance_worker.set_config(
                api_a=api_a, 
                api_b=api_b, 
                interval=self.auto_balance_interval,
                symbol=self.order_symbol
            )
            if not self.autobalance_worker.isRunning():
                self.autobalance_worker.start()
                
        else: # (중지 조건)
            if self.autobalance_worker and self.autobalance_worker.isRunning():
                self.autobalance_worker.stop()
                # (시그널 연결 해제)
                try:
                    self.signal_state_updated_for_worker.disconnect(self.autobalance_worker.update_states)
                except RuntimeError:
                    pass # 이미 연결이 끊어졌을 수 있음
                self.autobalance_worker = None

    @Slot()
    def on_set_leverage(self):
        """
        (React: handleSetLeverage)
        '레버리지 설정' 버튼 클릭 시 호출됩니다.
        """
        ex_id: Optional[ExchangeId] = self.combo_leverage_exchange.currentData()
        if not ex_id:
            self.add_log("레버리지를 설정할 거래소를 선택하세요.", LogLevel.WARN)
            return
            
        client = self.api_clients.get(ex_id)
        if not client:
            self.add_log(f"[{EXCHANGE_NAMES[ex_id]}] API 클라이언트가 없습니다.", LogLevel.ERROR)
            return
            
        leverage = self.spin_leverage.value()
        self.add_log(f"[{client.name}] [{self.order_symbol.value}] 레버리지를 {leverage}x로 설정 시도...", LogLevel.INFO)
        
        try:
            client.set_leverage(self.order_symbol, leverage)
            # (성공 시, API의 state_update 시그널이 대시보드를 갱신할 것임)
        except Exception as e:
            self.add_log(f"[{client.name}] 레버리지 설정 실패: {e}", LogLevel.ERROR)

    @Slot()
    def on_execute_strategy_order(self):
        """
        (React: handleExecuteStrategyOrder)
        '전략 주문 실행' 버튼 클릭 시 호출됩니다.
        """
        if not self.selected_A or not self.selected_B:
            self.add_log("전략 A, B 거래소를 모두 선택하세요.", LogLevel.WARN)
            return
            
        client_a = self.api_clients.get(self.selected_A)
        price_a = self.prices.get(self.selected_A)
        
        if not client_a or price_a is None:
            self.add_log(f"[{EXCHANGE_NAMES[self.selected_A]}] API가 연결되지 않았거나 가격 정보가 없습니다.", LogLevel.ERROR)
            return

        try:
            quantity = self.input_strategy_qty.input.value()
            offset = self.spin_strategy_offset.value()
            
            if quantity <= 0:
                self.add_log("수량은 0보다 커야 합니다.", LogLevel.WARN)
                return

            direction_a: Optional[Direction] = None
            if self.btn_strategy_A_Long.isChecked():
                direction_a = Direction.LONG
            elif self.btn_strategy_A_Short.isChecked():
                direction_a = Direction.SHORT
            else:
                self.add_log("전략 방향을 선택하세요 (롱/숏).", LogLevel.WARN)
                return
                
            # (React: price = currentPrice + signedOffset)
            # 롱(매수) 주문은 (현재가 - 오프셋)에 지정가를 걸어야 함
            # 숏(매도) 주문은 (현재가 + 오프셋)에 지정가를 걸어야 함
            signed_offset = -offset if direction_a == Direction.LONG else offset
            price = price_a + signed_offset
            
            self.add_log(f"[{client_a.name}] [{self.order_symbol.value}] 전략 주문 제출 시도: {direction_a.value} {quantity} @ {price:.2f} (지정가)", LogLevel.INFO)

            client_a.create_order(
                symbol=self.order_symbol,
                order_type=OrderType.LMT,
                direction=direction_a,
                quantity=quantity,
                price=price
            )
            # (성공 시, API의 orders_update 시그널이 테이블을 갱신할 것임)
            
        except Exception as e:
            self.add_log(f"[{client_a.name}] 전략 주문 실패: {e}", LogLevel.ERROR)


    @Slot()
    def on_stop_strategy(self):
        """(Python-only) '전략 중지' 버튼 - 모든 미체결 주문 취소로 대체"""
        self.add_log("[Strategy] '전략 중지' 요청. A 거래소의 모든 미체결 주문을 취소합니다.", LogLevel.WARN)
        if self.selected_A and self.api_clients.get(self.selected_A):
            try:
                self.api_clients[self.selected_A].cancel_all_orders(self.order_symbol)
            except Exception as e:
                self.add_log(f"[{EXCHANGE_NAMES[self.selected_A]}] 주문 취소 실패: {e}", LogLevel.ERROR)
        else:
            self.add_log("A 거래소가 선택/연결되지 않았습니다.", LogLevel.ERROR)

    @Slot()
    def on_execute_individual_order_A(self):
        self._execute_individual_order(self.selected_A)

    @Slot()
    def on_execute_individual_order_B(self):
        self._execute_individual_order(self.selected_B)

    def _execute_individual_order(self, ex_id: Optional[ExchangeId]):
        """
        (React: handleExecuteIndividualOrder)
        '개별 주문 실행' (A 또는 B) 버튼 클릭 시 호출됩니다.
        """
        if not ex_id:
            self.add_log("개별 주문: 거래소가 선택되지 않았습니다.", LogLevel.WARN)
            return
            
        client = self.api_clients.get(ex_id)
        current_price = self.prices.get(ex_id)
        ex_name = EXCHANGE_NAMES[ex_id]
        
        if not client:
            self.add_log(f"[{ex_name}] API가 연결되지 않았습니다.", LogLevel.ERROR)
            return

        try:
            # 1. 위젯에서 값 읽기
            is_mkt = getattr(self, f"btn_ind_{ex_id.value}_mkt").isChecked()
            is_long = getattr(self, f"btn_ind_{ex_id.value}_long").isChecked()
            quantity = getattr(self, f"spin_ind_{ex_id.value}_qty").value()
            offset = getattr(self, f"spin_ind_{ex_id.value}_offset").value()
            
            order_type = OrderType.MKT if is_mkt else OrderType.LMT
            direction = Direction.LONG if is_long else Direction.SHORT
            
            if quantity <= 0:
                self.add_log(f"[{ex_name}] 수량은 0보다 커야 합니다.", LogLevel.WARN)
                return

            # 2. 가격 계산
            price: Optional[float] = None
            if order_type == OrderType.LMT:
                if current_price is None:
                    self.add_log(f"[{ex_name}] 가격 정보가 없어 지정가 주문을 할 수 없습니다.", LogLevel.ERROR)
                    return
                # (React: signedOffset = direction === Direction.LONG ? -offset : offset)
                signed_offset = -offset if direction == Direction.LONG else offset
                price = current_price + signed_offset

            # 3. 주문 실행
            order_type_str = f"지정가 ({price:.2f})" if price is not None else "시장가"
            self.add_log(f"[{ex_name}] [{self.order_symbol.value}] 개별 주문 제출: {direction.value} {quantity} {order_type_str}", LogLevel.INFO)
            
            client.create_order(
                symbol=self.order_symbol,
                order_type=order_type,
                direction=direction,
                quantity=quantity,
                price=price
            )
            # (성공 시, API의 state/orders 시그널이 UI를 갱신할 것임)

        except Exception as e:
            self.add_log(f"[{ex_name}] 개별 주문 실패: {e}", LogLevel.ERROR)

    @Slot()
    def on_individual_max_A(self):
        self._set_individual_max_qty(self.selected_A)

    @Slot()
    def on_individual_max_B(self):
        self._set_individual_max_qty(self.selected_B)

    def _set_individual_max_qty(self, ex_id: Optional[ExchangeId]):
        """
        (React: handleMaxClick)
        'MAX' 버튼 클릭 시, 현재 포지션 청산 수량을 입력창에 설정합니다.
        """
        if not ex_id: return
        
        state = self.exchange_states.get(ex_id)
        if state and state.position.quantity > 0:
            qty = state.position.quantity
            current_dir = state.position.direction
            
            # (React: setQuantity(position.quantity.toFixed(8)))
            getattr(self, f"spin_ind_{ex_id.value}_qty").setValue(qty)
            
            # (React: setDirection(position.direction === Direction.LONG ? Direction.SHORT : Direction.LONG))
            if current_dir == Direction.LONG:
                getattr(self, f"btn_ind_{ex_id.value}_short").setChecked(True)
                getattr(self, f"btn_ind_{ex_id.value}_long").setChecked(False)
            else: # SHORT
                getattr(self, f"btn_ind_{ex_id.value}_long").setChecked(True)
                getattr(self, f"btn_ind_{ex_id.value}_short").setChecked(False)
        else:
            getattr(self, f"spin_ind_{ex_id.value}_qty").setValue(0.0)

    @Slot(int, int)
    def on_order_cancel_clicked(self, row, column):
        """
        (React: onCancel)
        '미체결 주문' 테이블의 '취소' 버튼(5번 열) 클릭 시 호출됩니다.
        """
        if column != 5: # 5번 열 (취소 버튼)이 아니면 무시
            return
            
        order_id_item = self.table_open_orders.item(row, 0) # 0번 열(거래소)에 order.id 숨김
        if not order_id_item:
            return
            
        order_id = order_id_item.data(Qt.ItemDataRole.UserRole) # 숨겨진 ID
        order = next((o for o in self.open_orders if o.id == order_id), None)
        
        if not order:
            self.add_log(f"주문 ID {order_id}를 찾을 수 없습니다.", LogLevel.ERROR)
            return

        client = self.api_clients.get(order.exchangeId)
        if not client:
            self.add_log(f"[{EXCHANGE_NAMES[order.exchangeId]}] API 클라이언트가 없습니다.", LogLevel.ERROR)
            return
            
        self.add_log(f"[{client.name}] 주문 취소 중... (ID: {order_id})", LogLevel.INFO)
        try:
            client.cancel_order(self.order_symbol, order_id)
            # (성공 시, API의 orders_update 시그널이 테이블을 갱신할 것임)
        except Exception as e:
            self.add_log(f"주문 {order_id} 취소 실패: {e}", LogLevel.ERROR)

    @Slot()
    def on_cancel_all_orders(self):
        """
        (React: handleCancelAllOrders)
        '전체 취소' 버튼 클릭 시 호출됩니다.
        """
        clients_to_cancel = set(o.exchangeId for o in self.open_orders)
        if not clients_to_cancel:
            self.add_log('취소할 미체결 주문이 없습니다.', LogLevel.INFO)
            return
            
        self.add_log(f"[{self.order_symbol.value}] 모든 미체결 주문 취소 시도...", LogLevel.WARN)
        try:
            for ex_id in clients_to_cancel:
                client = self.api_clients.get(ex_id)
                if client:
                    client.cancel_all_orders(self.order_symbol)
            self.add_log(f"[{self.order_symbol.value}] 모든 주문 취소 명령 전송 완료.", LogLevel.SUCCESS)
            # (성공 시, API의 orders_update 시그널이 테이블을 갱신할 것임)
        except Exception as e:
             self.add_log(f"[{self.order_symbol.value}] 전체 주문 취소 실패: {e}", LogLevel.ERROR)

    # --- 4. API Data Handlers (React: set... / useEffect) ---
    
    # (신규) AutoBalanceWorker로 상태를 보내기 위한 시그널
    signal_state_updated_for_worker = Signal(object, object)

    @Slot(ExchangeId, ExchangeState)
    def on_state_update(self, ex_id: ExchangeId, state: ExchangeState):
        """
        (React: setExchangeStates)
        API 클라이언트(Mock/Real)로부터 계정 상태(포지션, 잔고 등)를 받습니다.
        """
        self.exchange_states[ex_id] = state
        
        # 1. 헤더 (총 자산) 업데이트
        self.update_total_balance()
        
        # 2. 해당 대시보드 업데이트
        self.update_dashboard_by_id(ex_id, state)
        
        # 3. 레버리지 패널 (현재 레버리지) 업데이트
        self.update_leverage_panel_ui()
        
        # 4. AutoBalanceWorker로 최신 상태 전송
        # (A, B가 선택되었는지 확인)
        state_a = self.exchange_states.get(self.selected_A) if self.selected_A else None
        state_b = self.exchange_states.get(self.selected_B) if self.selected_B else None
        self.signal_state_updated_for_worker.emit(state_a, state_b)

    @Slot(ExchangeId, list)
    def on_orders_update(self, ex_id: ExchangeId, orders: List[Order]):
        """
        (React: setOpenOrders)
        API 클라이언트로부터 미체결 주문 목록을 받습니다.
        """
        # 1. 다른 거래소의 주문은 유지하고, 이 거래소의 주문만 교체
        other_orders = [o for o in self.open_orders if o.exchangeId != ex_id]
        self.open_orders = other_orders + orders
        
        # 2. 테이블 갱신
        self.update_open_orders_table()

    @Slot(ExchangeId, float)
    def on_price_update(self, ex_id: ExchangeId, price: float):
        """
        (React: setPrices)
        API 클라이언트로부터 현재가를 받습니다.
        """
        self.prices[ex_id] = price
        
        # 1. 헤더 (A, B 현재가) 업데이트
        if ex_id == self.selected_A:
            self.header_price_A.setText(f"${price:.2f}")
            # (StrategyPanel 오프셋 라벨)
            self.label_strategy_offset.setText(f"A 거래소 지정가 오프셋 (현재가: {price:.2f})")
        if ex_id == self.selected_B:
            self.header_price_B.setText(f"${price:.2f}")
            
        # 2. 개별 주문 (오프셋 라벨) 업데이트
        try:
            getattr(self, f"spin_ind_{ex_id.value}_offset").lineEdit().setPlaceholderText(f"오프셋 (현재가: {price:.2f})")
        except AttributeError:
            pass # (위젯이 아직 생성되지 않았을 수 있음)


    # --- 5. UI Update Slots (Helper functions) ---

    @Slot()
    def update_total_balance(self):
        """(React: totalAssets) 헤더의 총 자산을 계산하여 업데이트합니다."""
        total = sum(state.balance for state in self.exchange_states.values())
        self.header_total_assets.setText(f"${total:.2f}")

    @Slot()
    def update_open_orders_table(self):
        """(React: OpenOrdersPanel) '미체결 주문' 테이블을 갱신합니다."""
        self.table_open_orders.setRowCount(0) # 테이블 비우기
        
        if not self.open_orders:
            self.table_open_orders.setRowCount(1)
            placeholder = QTableWidgetItem("미체결 주문이 없습니다.")
            placeholder.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_open_orders.setItem(0, 0, placeholder)
            self.table_open_orders.setSpan(0, 0, 1, 6)
            return
            
        self.table_open_orders.setSpan(0, 0, 1, 1) # 스팬 제거
        
        self.table_open_orders.setRowCount(len(self.open_orders))
        
        for i, order in enumerate(self.open_orders):
            ex_name = EXCHANGE_NAMES[order.exchangeId]
            unfilled_qty = order.quantity - order.filledQuantity
            
            # (React: OrderRow)
            item_ex = QTableWidgetItem(ex_name)
            item_ex.setData(Qt.ItemDataRole.UserRole, order.id) # (취소용 ID 숨기기)
            
            item_dir_icon = IconLabel('long' if order.direction == Direction.LONG else 'short')
            
            item_qty = QTableWidgetItem(f"{order.quantity:.5f}")
            item_qty.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            item_unfilled = QTableWidgetItem(f"{unfilled_qty:.5f}")
            item_unfilled.setObjectName("OrderQtyUnfilled")
            item_unfilled.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            item_price = QTableWidgetItem(f"{order.price:.2f}")
            item_price.setObjectName("OrderPrice")
            item_price.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            btn_cancel = QPushButton("취소")
            btn_cancel.setObjectName("BtnCancel")
            
            self.table_open_orders.setItem(i, 0, item_ex)
            self.table_open_orders.setCellWidget(i, 1, item_dir_icon)
            self.table_open_orders.setItem(i, 2, item_qty)
            self.table_open_orders.setItem(i, 3, item_unfilled)
            self.table_open_orders.setItem(i, 4, item_price)
            self.table_open_orders.setCellWidget(i, 5, btn_cancel)

    @Slot(str)
    def on_api_combo_changed(self, text: str):
        """(React: ApiSettings) 'API 설정' 콤보박스 변경 시 입력창을 토글합니다."""
        ex_id: ExchangeId = self.combo_api_exchange.currentData()
        
        is_pacifica = (ex_id == ExchangeId.PACIFICA)
        self.api_input_address.label.setVisible(is_pacifica)
        self.api_input_address.input.setVisible(is_pacifica)
        self.api_input_address.description.setVisible(is_pacifica)
        
        is_lighter = (ex_id == ExchangeId.LIGHTER)
        self.api_input_account_id.label.setVisible(is_lighter)
        self.api_input_account_id.input.setVisible(is_lighter)
        self.api_input_account_id.description.setVisible(is_lighter)
        self.api_input_l1_address.label.setVisible(is_lighter)
        self.api_input_l1_address.input.setVisible(is_lighter)
        self.api_input_l1_address.description.setVisible(is_lighter)

    @Slot()
    def update_api_settings_ui(self):
        """(React: ApiSettings) '인증된 거래소' 목록 UI를 갱신합니다."""
        # 1. '저장 및 인증' 버튼 상태
        ex_id: ExchangeId = self.combo_api_exchange.currentData()
        verifying = self.is_verifying.get(ex_id, False)
        
        self.btn_api_save.setEnabled(not verifying)
        self.btn_api_save.setText("인증 중..." if verifying else "저장 및 인증")
        
        # 2. '인증된 거래소' 리스트
        self.list_auth_exchanges.clear()
        if not self.authenticated_exchanges:
            self.list_auth_exchanges.addItem("없음")
        else:
            for ex_id in self.authenticated_exchanges:
                item = QListWidgetItem(EXCHANGE_NAMES[ex_id])
                item.setIcon(QIcon(self.create_status_icon(True))) # (connected)
                self.list_auth_exchanges.addItem(item)
                
        # 3. '전략 거래소' 콤보박스 갱신
        self.update_strategy_selector_ui()
        self.update_leverage_panel_ui()


    @Slot()
    def update_strategy_selector_ui(self):
        """
        (React: StrategySelector) '전략 거래소' 콤보박스를 갱신합니다.
        (수정) 무한 루프를 막기 위해 blockSignals() 추가
        """
        # (수정) 시그널 차단
        self.combo_strategy_A.blockSignals(True)
        self.combo_strategy_B.blockSignals(True)
        
        current_A = self.combo_strategy_A.currentData()
        current_B = self.combo_strategy_B.currentData()
        
        self.combo_strategy_A.clear()
        self.combo_strategy_B.clear()
        
        self.combo_strategy_A.addItem("-- 선택 --", None)
        self.combo_strategy_B.addItem("-- 선택 --", None)
        
        # A 콤보박스 채우기 (B에서 선택된 것 제외)
        for ex_id in self.authenticated_exchanges:
            if ex_id != current_B:
                self.combo_strategy_A.addItem(EXCHANGE_NAMES[ex_id], ex_id)
        
        # B 콤보박스 채우기 (A에서 선택된 것 제외)
        for ex_id in self.authenticated_exchanges:
            if ex_id != current_A:
                self.combo_strategy_B.addItem(EXCHANGE_NAMES[ex_id], ex_id)
        
        # 이전 선택 유지
        if current_A and current_A in self.authenticated_exchanges:
            self.combo_strategy_A.setCurrentText(EXCHANGE_NAMES[current_A])
        if current_B and current_B in self.authenticated_exchanges:
            self.combo_strategy_B.setCurrentText(EXCHANGE_NAMES[current_B])
            
        # (수정) 시그널 차단 해제
        self.combo_strategy_A.blockSignals(False)
        self.combo_strategy_B.blockSignals(False)

    @Slot()
    def update_leverage_panel_ui(self):
        """
        (React: LeverageControl) '레버리지 설정' 콤보박스와 라벨을 갱신합니다.
        (수정) 무한 루프를 막기 위해 blockSignals() 추가
        """
        # (수정) 시그널 차단
        self.combo_leverage_exchange.blockSignals(True)
        
        current_ex_id: Optional[ExchangeId] = self.combo_leverage_exchange.currentData()
        
        self.combo_leverage_exchange.clear()
        
        if not self.authenticated_exchanges:
            self.combo_leverage_exchange.addItem("-- 인증된 거래소 없음 --", None)
        else:
            for ex_id in self.authenticated_exchanges:
                self.combo_leverage_exchange.addItem(EXCHANGE_NAMES[ex_id], ex_id)

        # 이전 선택 유지
        if current_ex_id and current_ex_id in self.authenticated_exchanges:
            self.combo_leverage_exchange.setCurrentText(EXCHANGE_NAMES[current_ex_id])
        elif not current_ex_id and self.authenticated_exchanges:
            # (React: useEffect) - 첫 번째 항목을 기본값으로 선택
            current_ex_id = self.authenticated_exchanges[0]
            self.combo_leverage_exchange.setCurrentText(EXCHANGE_NAMES[current_ex_id])
        
        # (수정) 시그널 차단 해제
        self.combo_leverage_exchange.blockSignals(False)
            
        self.on_leverage_combo_changed() # 라벨 갱신

    @Slot()
    def on_leverage_combo_changed(self):
        """(React: LeverageControl) 레버리지 콤보박스 변경 시 라벨을 갱신합니다."""
        ex_id: Optional[ExchangeId] = self.combo_leverage_exchange.currentData()
        current_leverage = "N/A"
        
        if ex_id and ex_id in self.exchange_states:
            current_leverage = str(self.exchange_states[ex_id].leverage)
            
        self.label_leverage.setText(f"레버리지 (현재: {current_leverage}x)")

    @Slot()
    def update_dashboard_targets(self):
        """'전략 거래소' 선택(A, B)에 따라 대시보드 (A, B)의 타겟을 변경합니다."""
        # 1. 대시보드 A
        if self.selected_A:
            state = self.exchange_states.get(self.selected_A)
            self.update_dashboard_by_id(self.selected_A, state) # state가 None이어도 갱신
        else:
            self.update_dashboard_by_id(ExchangeId.PACIFICA, None, is_reset=True)

        # 2. 대시보드 B
        if self.selected_B:
            state = self.exchange_states.get(self.selected_B)
            self.update_dashboard_by_id(self.selected_B, state)
        else:
            self.update_dashboard_by_id(ExchangeId.LIGHTER, None, is_reset=True)
            
    def update_dashboard_by_id(self, ex_id: ExchangeId, state: Optional[ExchangeState], is_reset: bool = False):
        """(React: Dashboard) ID에 해당하는 대시보드 UI를 갱신합니다."""
        
        # (중요) 대시보드 A, B가 어떤 ex_id를 표시할지 결정
        # (A가 선택되면 dash_card_pacifica가 A를 표시, B가 선택되면 dash_card_lighter가 B를 표시)
        if ex_id == self.selected_A:
            dash_id = ExchangeId.PACIFICA # (UI 슬롯 1번)
        elif ex_id == self.selected_B:
            dash_id = ExchangeId.LIGHTER # (UI 슬롯 2번)
        else:
            # (선택되지 않은 거래소의 상태 업데이트는 무시)
            return

        card = getattr(self, f"dash_card_{dash_id.value}")
        dash_pos = getattr(self, f"dash_pos_{dash_id.value}")
        dash_qty = getattr(self, f"dash_qty_{dash_id.value}")
        dash_entry_label = getattr(self, f"dash_entry_label_{dash_id.value}")
        dash_entry = getattr(self, f"dash_entry_{dash_id.value}")
        dash_leverage = getattr(self, f"dash_leverage_{dash_id.value}")
        dash_pnl = getattr(self, f"dash_pnl_{dash_id.value}")
        dash_balance = getattr(self, f"dash_balance_{dash_id.value}")
        
        if state is None or is_reset:
            # (React: if (!state))
            card.set_title("거래소 미선택")
            dash_pos.setText("없음")
            dash_pos.setObjectName("DashValueNone")
            dash_qty.setText("0.00000")
            dash_entry_label.hide()
            dash_entry.hide()
            dash_leverage.setText("N/Ax")
            dash_pnl.setText("0.00")
            dash_pnl.setObjectName("DashValuePnlZero")
            dash_balance.setText("0.00")
            return

        # (React: const directionStyle = ...)
        pos = state.position
        has_position = (pos.quantity > 0)
        
        card.set_title(state.name)
        
        if pos.direction == Direction.LONG:
            dash_pos.setText("▲ 롱")
            dash_pos.setObjectName("DashValueLong")
        elif pos.direction == Direction.SHORT:
            dash_pos.setText("▼ 숏")
            dash_pos.setObjectName("DashValueShort")
        else:
            dash_pos.setText("없음")
            dash_pos.setObjectName("DashValueNone")
            
        dash_qty.setText(f"{pos.quantity:.5f}")
        
        # (React: {hasPosition && ...})
        dash_entry_label.setVisible(has_position)
        dash_entry.setVisible(has_position)
        dash_entry.setText(f"${pos.entryPrice:.2f}")

        dash_leverage.setText(f"{state.leverage}x")
        
        # (React: formatPnl)
        pnl = state.pnl
        dash_pnl.setText(f"{pnl:+.2f}" if pnl != 0 else f"{pnl:.2f}")
        if pnl > 0:
            dash_pnl.setObjectName("DashValuePnlPositive")
        elif pnl < 0:
            dash_pnl.setObjectName("DashValuePnlNegative")
        else:
            dash_pnl.setObjectName("DashValuePnlZero")

        dash_balance.setText(f"{state.balance:.2f} {state.currency}")

    def update_all_dashboards(self):
        """(신규) A, B 선택에 따라 대시보드를 갱신합니다."""
        state_a = self.exchange_states.get(self.selected_A) if self.selected_A else None
        state_b = self.exchange_states.get(self.selected_B) if self.selected_B else None
        
        self.update_dashboard_by_id(ExchangeId.PACIFICA, state_a, is_reset=not self.selected_A)
        self.update_dashboard_by_id(ExchangeId.LIGHTER, state_b, is_reset=not self.selected_B)


    @Slot()
    def update_individual_order_targets(self):
        """'전략 거래소' 선택(A, B)에 따라 개별 주문 패널 (A, B)의 타겟을 변경합니다."""
        
        # (UI 슬롯 1번: A)
        card_a = self.individual_order_A
        ex_id_a = self.selected_A
        if ex_id_a:
            card_a.set_title(f"개별 주문: {EXCHANGE_NAMES[ex_id_a]}")
            card_a.setEnabled(True)
        else:
            card_a.set_title("개별 주문 (A 미선택)")
            card_a.setEnabled(False)
            
        # (UI 슬롯 2번: B)
        card_b = self.individual_order_B
        ex_id_b = self.selected_B
        if ex_id_b:
            card_b.set_title(f"개별 주문: {EXCHANGE_NAMES[ex_id_b]}")
            card_b.setEnabled(True)
        else:
            card_b.set_title("개별 주문 (B 미선택)")
            card_b.setEnabled(False)


    # --- 6. Utility ---

    def stop_all_workers(self):
        """앱 종료 또는 재연결 시 모든 스레드/API를 중지합니다."""
        self.add_log("Stopping all background workers and API streams...", LogLevel.INFO)
        
        # 1. 자동 균형 스레드 중지
        if self.autobalance_worker and self.autobalance_worker.isRunning():
            self.autobalance_worker.stop()
            self.autobalance_worker.wait(2000) # 2초 대기
        self.autobalance_worker = None
        
        # 2. 모든 API 클라이언트 스트리밍 중지 (QTimer 중지)
        for client in self.api_clients.values():
            client.stop_streaming()
            
        self.loading_indicator.stop() 

    @Slot()
    def set_button_group(self, other_button, checked):
        """(React: useState) 버튼 그룹(Checkable)에서 하나만 선택되도록 합니다."""
        # (버튼 클릭 시, 다른 버튼의 체크를 해제)
        if self.sender().isChecked():
            other_button.setChecked(False)
        else:
            # (체크 해제를 방지 - 항상 하나는 선택되어야 함)
            self.sender().setChecked(True)

    def create_status_icon(self, is_connected):
        """상태 아이콘(빨강/초록)을 QPixmap으로 생성합니다."""
        pixmap = QPixmap(10, 10)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        # (React: bg-green-500, bg-red-500)
        color = QColor("#94E2D5") if is_connected else QColor("#F38BA8") 
        painter.setBrush(color)
        painter.setPen(Qt.GlobalColor.transparent)
        painter.drawEllipse(0, 0, 10, 10)
        painter.end()
        return QIcon(pixmap)

    @Slot(str, LogLevel)
    def add_log(self, message: str, level: LogLevel = LogLevel.INFO):
        """
        (React: addLog)
        시스템 로그 위젯에 메시지를 추가합니다.
        """
        # (React: [...prev.slice(-200), newLog])
        if len(self.logs) > 200:
            self.logs.pop(0)
            
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        log_entry = LogEntry(timestamp=timestamp, level=level, message=message)
        self.logs.append(log_entry)
        
        print(f"[{timestamp}] [{level.value}] {message}") # 콘솔 출력
        logging.info(f"[{level.value}] {message}") # 파일 출력
        
        # (React: LogPanel 렌더링)
        # (QTextEdit은 HTML 서식을 지원함)
        color = "#A6ADC8" # (INFO)
        if level == LogLevel.SUCCESS: color = "#94E2D5"
        elif level == LogLevel.WARN: color = "#FAB387"
        elif level == LogLevel.ERROR: color = "#F38BA8"
        
        log_html = (
            f"<span style='color: #7F849C;'>[{log_entry.timestamp}]</span> "
            f"<span style='color: {color}; font-weight: bold;'>[{log_entry.level.value}]</span> "
            f"<span style='color: #BAC2DE;'>{log_entry.message}</span>"
        )
        self.log_widget.append(log_html)
        
        # (React: scrollRef.current.scrollTop)
        self.log_widget.verticalScrollBar().setValue(
            self.log_widget.verticalScrollBar().maximum()
        )

    @Slot()
    def not_implemented(self):
        """미구현 기능 클릭 시 로그를 남깁니다."""
        sender = self.sender()
        self.add_log(f"Button '{sender.text()}' clicked, but not yet implemented.", LogLevel.WARN)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())