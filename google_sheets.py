"""
Google Sheets API 실시간 직접 연동 모듈 (GIDC 광장부동산 챗봇 전용)
- 사장님의 'chatbot' 구글 시트 (ID: 1lWMlwxRLNi9cHHhJeueMk4zmIXYOCYsJJY7GRZ2deik)
- 깃허브 업로드나 서버 재시작 없이 구글 시트를 고치는 순간 즉시 챗봇에 반영됨
"""

import urllib.request
import urllib.parse
import json

SPREADSHEET_ID = "1lWMlwxRLNi9cHHhJeueMk4zmIXYOCYsJJY7GRZ2deik"

def get_sheet_data_as_csv(sheet_name: str = "") -> str:
    """
    지정된 구글 시트 탭의 데이터를 실시간으로 읽어옵니다.
    """
    try:
        if sheet_name:
            encoded_sheet = urllib.parse.quote(sheet_name)
            url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_sheet}"
        else:
            url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv"
            
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            csv_text = response.read().decode("utf-8").strip()
            return csv_text
    except Exception as e:
        print(f"[Google Sheets Fetch Warning ({sheet_name})]: {e}")
        return ""

def get_live_google_sheets_knowledge() -> str:
    """
    구글 스프레드시트의 전체 탭(FAQ, 매물 등) 데이터를 통째로 합쳐서 반환합니다.
    """
    data_parts = []
    
    # 1. 기본 시트 데이터
    default_data = get_sheet_data_as_csv("")
    if default_data and len(default_data) > 5:
        data_parts.append(f"[구글 시트 지식 데이터]\n{default_data}")

    # 2. FAQ 탭 데이터
    faq_data = get_sheet_data_as_csv("FAQ")
    if faq_data and faq_data != default_data and len(faq_data) > 5:
        data_parts.append(f"[구글 시트 FAQ 데이터]\n{faq_data}")

    # 3. 매물 탭 데이터
    property_data = get_sheet_data_as_csv("매물")
    if property_data and property_data != default_data and len(property_data) > 5:
        data_parts.append(f"[구글 시트 매물 시세 데이터]\n{property_data}")

    combined = "\n\n".join(data_parts).strip()
    return combined
