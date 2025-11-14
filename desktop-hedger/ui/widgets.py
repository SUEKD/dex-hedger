import sys
from PySide6.QtCore import (
    Qt, Property, QSize, QPoint, QRectF, QEasingCurve, QPropertyAnimation, 
    Slot, Signal, QTimer
)
from PySide6.QtGui import QColor, QBrush, QPaintEvent, QPen, QPainter
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit, 
    QWidget, QSizePolicy, QSpinBox, QDoubleSpinBox, QVBoxLayout
)

# 1. ToggleSwitch (AutoBalancePanel.tsx의 토글)
class ToggleSwitch(QCheckBox):
    """
    스타일이 적용된 토글 스위치 위젯.
    QCheckBox를 상속받아, 체크 상태에 따라 애니메이션 효과를 줍니다.
    """
    _transparent_pen = QPen(Qt.GlobalColor.transparent)
    _light_grey_pen = QPen(QColor("#585B70")) # 테두리

    def __init__(
        self,
        parent=None,
        bar_color=QColor("#313244"), # 바 배경
        handle_color=QColor("#CDD6F4"), # 핸들 (Off)
        checked_bar_color=QColor("#89B4FA"), # 바 배경 (On)
        checked_handle_color=QColor("#1E1E2E"), # 핸들 (On)
    ):
        super().__init__(parent)

        # 스타일시트 대신 QPainter를 사용하여 직접 그립니다.
        self.setFixedSize(52, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Colors
        self._bar_brush = QBrush(bar_color)
        self._bar_checked_brush = QBrush(checked_bar_color)

        self._handle_brush = QBrush(handle_color)
        self._handle_checked_brush = QBrush(checked_handle_color)

        # Animation
        self._handle_position = 0
        self.animation = QPropertyAnimation(self, b"handle_position", self)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.setDuration(150) # ms

        self.toggled.connect(self.on_state_changed)

    def paintEvent(self, e: QPaintEvent):
        """위젯의 모양을 직접 그립니다."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(self._transparent_pen)

        bar_rect = QRectF(0, 0, self.width(), self.height())
        bar_radius = self.height() / 2

        # 1. Draw Bar
        p.setBrush(self._bar_checked_brush if self.isChecked() else self._bar_brush)
        p.drawRoundedRect(bar_rect, bar_radius, bar_radius)

        # 2. Draw Handle
        p.setBrush(self._handle_checked_brush if self.isChecked() else self._handle_brush)
        
        # 3. Draw Handle Outline (테두리)
        p.setPen(self._light_grey_pen if not self.isChecked() else self._transparent_pen)

        padding = 4 # 핸들과 바 사이의 여백
        handle_diameter = self.height() - 2 * padding
        handle_radius = handle_diameter / 2
        
        handle_x = self.handle_position + padding

        handle_rect = QRectF(
            handle_x, padding, 
            handle_diameter, handle_diameter
        )
        p.drawEllipse(handle_rect)
        p.end()

    @Slot(bool)
    def on_state_changed(self, checked):
        """체크 상태 변경 시 애니메이션을 트리거합니다."""
        padding = 4
        
        start_value = 0
        end_value = self.width() - self.height()
        
        self.animation.stop()
        
        if checked:
            self.animation.setStartValue(self._handle_position)
            self.animation.setEndValue(end_value)
        else:
            self.animation.setStartValue(self._handle_position)
            self.animation.setEndValue(start_value)
            
        self.animation.start()

    @Property(float)
    def handle_position(self):
        """애니메이션이 사용할 핸들의 x 위치 속성"""
        return self._handle_position

    @handle_position.setter
    def handle_position(self, value):
        """애니메이션이 이 setter를 호출하여 _handle_position을 업데이트합니다."""
        self._handle_position = value
        self.update() # 값이 변경될 때마다 위젯을 다시 그리도록 강제

    def hitButton(self, pos: QPoint):
        """위젯의 어느 부분을 클릭해도 체크 상태가 변경되도록 합니다."""
        return self.contentsRect().contains(pos)


# 2. Card (Card.tsx)
class Card(QFrame):
    """
    React 'Card' 컴포넌트를 PySide6 QFrame으로 구현합니다.
    {title} / {children} 구조를 가집니다.
    """
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("Card") # 스타일시트 적용을 위해
        
        # 전체 카드 레이아웃 (VBox)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(6, 6, 6, 6) # p-1.5 (Tailwind)
        self.main_layout.setSpacing(4) # space-y-1.5
        
        # 1. 타이틀
        self.title_label = QLabel(title)
        self.title_label.setObjectName("CardTitle") # 스타일시트 적용을 위해
        
        # 2. 컨텐츠 (자식 위젯이 추가될 곳)
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(5) # space-y-1.5

        self.main_layout.addWidget(self.title_label)
        self.main_layout.addLayout(self.content_layout, 1) # content가 남은 공간 차지

    def set_title(self, title_text):
        """카드의 타이틀을 변경합니다."""
        self.title_label.setText(title_text)

    def add_widget(self, widget, stretch=0):
        """카드의 {children} 영역에 위젯을 추가합니다."""
        self.content_layout.addWidget(widget, stretch)
        
    def add_layout(self, layout, stretch=0):
        """카드이 {children} 영역에 레이아웃을 추가합니다."""
        self.content_layout.addLayout(layout, stretch)

# 3. StackedInput (ApiSettings.tsx의 입력창)
class StackedInput(QVBoxLayout):
    """
    레이블 (상단)
    [입력창] (중간)
    설명 (하단)
    형태의 (세로) 레이아웃을 생성합니다.
    """
    def __init__(self, label_text, placeholder_text="", description_text="", is_password=False):
        super().__init__()
        self.setSpacing(4) # 위젯 간 간격

        self.label = QLabel(label_text)
        self.label.setObjectName("InputLabel") # 스타일시트

        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder_text)
        
        if is_password:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)

        self.description = QLabel(description_text)
        self.description.setObjectName("InputDescription") # 스타일시트

        self.addWidget(self.label)
        self.addWidget(self.input)
        self.addWidget(self.description)

# 4. IconLabel (icons.tsx)
class IconLabel(QLabel):
    """
    LongIcon, ShortIcon을 Unicode 문자로 대체합니다.
    """
    def __init__(self, icon_type='long'):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if icon_type == 'long':
            self.setText("▲") # Long
            self.setObjectName("LongIcon") # Green
        else:
            self.setText("▼") # Short
            self.setObjectName("ShortIcon") # Red

# 5. LoadingIndicator (이전 Python 코드에서 유지)
class LoadingIndicator(QLabel):
    """
    텍스트 기반 로딩 인디케이터.
    """
    def __init__(self):
        super().__init__("Loading")
        self.setFixedSize(60, 20) 
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._update_text)
        self._animation_timer.setInterval(300) # 0.3초마다
        self._dot_count = 0
        
        self.hide() # 기본적으로 숨김

    @Slot()
    def _update_text(self):
        """타이머에 의해 호출되어 텍스트를 "Loading..."으로 변경합니다."""
        self._dot_count = (self._dot_count + 1) % 4 # 0, 1, 2, 3
        dots = "." * self._dot_count
        self.setText(f"Loading{dots.ljust(3)}") 

    def start(self):
        self.show()
        self._dot_count = 0
        self.setText("Loading")
        self._animation_timer.start()

    def stop(self):
        self._animation_timer.stop()
        self.hide()

# 6. TitleLabel (Card 타이틀 외의 제목)
class TitleLabel(QLabel):
    """
    스타일시트에서 'TitleLabel' 이름으로 참조할 수 있도록
    커스텀 클래스로 QLabel을 상속합니다.
    (Card의 타이틀보다 상위 제목에 사용)
    """
    def __init__(self, text=""):
        super().__init__(text)
        self.setObjectName("TitleLabel")
        
# 7. LabeledInput (가로 입력창 - 레버리지, 자동균형 등)
class LabeledInput(QHBoxLayout):
    """
    "레이블: [입력창]" 형태의 (가로) 레이아웃을 생성합니다.
    """
    def __init__(self, label_text, default_value="", input_width=None, input_type=None):
        super().__init__()
        
        self.label = QLabel(label_text)
        
        if input_type == 'int':
            self.input = QSpinBox()
            self.input.setRange(0, 999999)
            if default_value:
                self.input.setValue(int(default_value))
        elif input_type == 'float':
            self.input = QDoubleSpinBox()
            self.input.setRange(0, 999999.99)
            self.input.setDecimals(4)
            if default_value:
                self.input.setValue(float(default_value))
        else:
            self.input = QLineEdit()
            if default_value:
                self.input.setText(default_value)

        if input_width:
            self.input.setFixedWidth(input_width)
            
        self.addWidget(self.label)
        self.addWidget(self.input, 1) # 입력창이 남은 공간을 차지