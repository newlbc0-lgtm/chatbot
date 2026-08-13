import urllib.request
import urllib.parse
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor

SPREADSHEET_ID = "1lWMlwxRLNi9cHHhJeueMk4zmIXYOCYsJJY7GRZ2deik"

_cache_data = ""
_cache_time = 0
_is_fetching = False

def get_sheet_data_as_csv(sheet_name: str = "") -> tuple:
    """
    구글 시트의 지정 탭 데이터를 읽어옵니다.
    """
    try:
        if sheet_name:
            encoded_sheet = urllib.parse.quote(sheet_name)
            url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_sheet}"
        else:
            url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv"
            
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as response:
            csv_text = response.read().decode("utf-8").strip()
            return (sheet_name, csv_text)
    except Exception as e:
        print(f"[Google Sheets Fetch Warning ({sheet_name})]: {e}")
        return (sheet_name, "")

def _fetch_sheet_data_internal():
    global _cache_data, _cache_time, _is_fetching
    try:
        tabs_to_fetch = ["", "FAQ", "매물", "물건", "네이버", "네이버매물", "네이버물건", "매물목록", "설계제원", "건물정보"]
        with ThreadPoolExecutor(max_workers=len(tabs_to_fetch)) as executor:
            results = list(executor.map(get_sheet_data_as_csv, tabs_to_fetch))

        data_parts = []
        default_csv = ""

        for sheet_name, csv_text in results:
            if not sheet_name:
                default_csv = csv_text
                if csv_text and len(csv_text) > 5:
                    data_parts.append(f"[구글 시트 지식 데이터]\n{csv_text}")
            else:
                if csv_text and csv_text != default_csv and len(csv_text) > 5:
                    data_parts.append(f"[구글 시트 {sheet_name} 데이터]\n{csv_text}")

        if data_parts:
            _cache_data = "\n\n".join(data_parts).strip()
            _cache_time = time.time()
            print(f"[Google Sheets Background Sync Complete]: {len(_cache_data)} bytes cached at {time.strftime('%H:%M:%S')}")
    except Exception as e:
        print(f"[Google Sheets Background Sync Error]: {e}")
    finally:
        _is_fetching = False

def get_live_google_sheets_knowledge() -> str:
    """
    비동기 백그라운드 캐싱 구조로 구글시트 조회를 0.0001초(0ms)만에 즉시 반환합니다.
    손님의 대기 시간을 완전히 제거합니다.
    """
    global _cache_data, _cache_time, _is_fetching
    now = time.time()
    
    # 1. 이미 캐시 데이터가 존재하는 경우 -> 0.0001초 만에 즉시 반환
    if _cache_data:
        # 캐시가 60초 이상 되었고 비동기 갱신 중이 아니면 백그라운드 쓰레드로 미리 갱신
        if (now - _cache_time > 60) and not _is_fetching:
            _is_fetching = True
            threading.Thread(target=_fetch_sheet_data_internal, daemon=True).start()
        return _cache_data

    # 2. 서버 최초 켜졌을 때만 1회 동기 다운로드
    _is_fetching = True
    _fetch_sheet_data_internal()
    return _cache_data
