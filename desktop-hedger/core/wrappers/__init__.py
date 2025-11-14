from .pacifica import PacificaAPI
# (수정) lighter_api.py -> lighter.py (SDK가 합쳐진 거대 파일)
from .lighter import LighterAPI

# core/types.py에서 ExchangeId를 가져옴
from core.types import ExchangeId, EXCHANGE_NAMES

# (수정) React의 ExchangeId.PACIFICA ('pacifica') Enum을 키로 사용
EXCHANGE_MAP = {
    ExchangeId.PACIFICA: PacificaAPI,
    ExchangeId.LIGHTER: LighterAPI,
}

# (신규) ExchangeId Enum을 이름 문자열(trade.kor)로 변환하기 위한 맵
# (참고) React에서는 EXCHANGE_NAMES['pacifica'] -> "Pacifica"
# (참고) Python에서는 EXCHANGE_NAMES[ExchangeId.PACIFICA] -> "Pacifica"
EXCHANGE_ID_MAP = {
    EXCHANGE_NAMES[ExchangeId.PACIFICA]: ExchangeId.PACIFICA,
    EXCHANGE_NAMES[ExchangeId.LIGHTER]: ExchangeId.LIGHTER,
}