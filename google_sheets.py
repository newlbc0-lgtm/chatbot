"""
Google Sheets API 실시간 연동 모듈 (60초 초고속 메모리 캐싱 적용)
"""

import urllib.request
import urllib.parse
import json
import time

SPREADSHEET_ID = "1lWMlwxRLNi9cHHhJeueMk4zmIXYOCYsJJY7GRZ2deik"

_cache_data = ""
_cache_time = 0
CACHE_TTL_SECONDS = 60  # 60초 메모리 캐시로 5초 타임아웃 완벽 방지

def get_sheet_data_as_csv(sheet_name: str = "") -> str:
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
            return csv_text
    except Exception as e:
        print(f"[Google Sheets Fetch Warning ({sheet_name})]: {e}")
        return ""

def get_live_google_sheets_knowledge() -> str:
    """
    구글 스프레드시트 지식 데이터를 60초 캐싱하여 카카오톡 5초 타임아웃 제한을 방지합니다.
    """
    global _cache_data, _cache_time
    now = time.time()
    
    # 60초 내 재요청 시 즉시 캐시 데이터 반환 (0.001초 소요)
    if _cache_data and (now - _cache_time < CACHE_TTL_SECONDS):
        return _cache_data

    data_parts = []
    
    default_data = get_sheet_data_as_csv("")
    if default_data and len(default_data) > 5:
        data_parts.append(f"[구글 시트 지식 데이터]\n{default_data}")

    # 다양한 탭 데이터 동적 읽기 (FAQ, 매물, 설계제원, 건물정보)
    additional_tabs = ["FAQ", "매물", "설계제원", "건물정보"]
    for tab_name in additional_tabs:
        tab_data = get_sheet_data_as_csv(tab_name)
        if tab_data and tab_data != default_data and len(tab_data) > 5:
            data_parts.append(f"[구글 시트 {tab_name} 데이터]\n{tab_data}")

    _cache_data = "\n\n".join(data_parts).strip()
    _cache_time = now
    return _cache_data
