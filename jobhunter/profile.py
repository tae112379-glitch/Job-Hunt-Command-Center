"""희망 직무 프로필: GPS 송수신 캡스톤 + 네트워크/SW 직무.

가중치가 높을수록 해당 키워드가 공고 적합도에 크게 기여한다.
소문자로 비교하므로 영문은 소문자로 적는다.
"""

PROFILE_KEYWORDS: dict[str, dict[str, int]] = {
    "gps": {  # 캡스톤 직결
        "gps": 5, "gnss": 5, "위성항법": 5, "위치기반": 3, "측위": 4, "nmea": 5,
        "rtk": 4, "imu": 2, "ublox": 3, "u-blox": 3, "위성": 2,
    },
    "network": {
        "네트워크": 4, "network": 3, "tcp": 3, "udp": 3, "tcp/ip": 4, "lte": 3,
        "5g": 3, "rf": 3, "무선통신": 4, "통신": 2, "프로토콜": 3, "protocol": 3,
        "socket": 3, "소켓": 3, "wifi": 2, "bluetooth": 2, "lora": 3, "mqtt": 3,
        "라우팅": 3, "routing": 3, "ccna": 3,
    },
    "software": {
        "python": 3, "c++": 3, "c언어": 2, "embedded": 4, "임베디드": 4,
        "펌웨어": 4, "firmware": 4, "rtos": 3, "linux": 2, "리눅스": 2,
        "백엔드": 2, "backend": 2, "sw": 1, "소프트웨어": 1, "신호처리": 3,
        "dsp": 3, "fpga": 2, "stm32": 3, "arm": 2,
    },
}

# 있으면 감점 (희망 직무와 거리가 먼 직군)
NEGATIVE_KEYWORDS: dict[str, int] = {
    "영업": -4, "마케팅": -4, "회계": -4, "디자이너": -3, "경력 10년": -5,
    "sales": -4, "marketing": -4,
}

CATEGORY_LABELS = {"gps": "GPS/위치", "network": "네트워크/통신", "software": "SW/임베디드"}
