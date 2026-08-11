# 🤖 GIDC 광장부동산 24시간 듀얼 챗봇 (Google Sheets 실시간 연동 + Claude AI)

> **작성 일시**: 2026년 8월 11일  
> **프로젝트 경로**: `d:\python-prg\chatbot`  
> **구글 스프레드시트 링크**: [chatbot 구글 시트 직접가기](https://docs.google.com/spreadsheets/d/1lWMlwxRLNi9cHHhJeueMk4zmIXYOCYsJJY7GRZ2deik/edit?usp=sharing)  
> **깃허브 저장소**: `https://github.com/newlbc0-lgtm/chatbot`  
> **Render 클라우드 서버**: `https://chatbot-9g4i.onrender.com`  
> **최종 상태**: ✅ 구글 스프레드시트 실시간 API 연동 + Claude AI 지식 엔진 100% 구축 완료

---

## 1. 📊 구글 스프레드시트 실시간 연동 아키텍처

사장님이 **`chatbot` 구글 시트**에 매물/FAQ를 입력하시면, 백엔드 서버가 **0.1초 만에 직접 API로 읽어서 챗봇에 즉시 반영**합니다. (코드 수정이나 깃허브 업로드가 전혀 필요 없습니다!)

```text
  [ 사장님 / 실장님 ] ──▶ 스마트폰/PC에서 구글 시트 입력 (https://docs.google.com/spreadsheets/d/1lWMlwxRLNi9cHHhJeueMk4zmIXYOCYsJJY7GRZ2deik)
                               │
                               ▼ (Google Sheets API 실시간 직접 통신 - 0.1초)
  [ Render FastAPI 서버 ] ─────┼─────▶ [ 🧠 Claude AI (LLM) ]
                               │
                               ▼ (손님 대화 발송)
  [ 카카오톡 & 네이버 톡톡 손님 대화창 ]
```

---

## 2. 🔗 전체 시스템 핵심 URL 모음

| 구분 | URL 주소 | 용도 및 설명 |
| :--- | :--- | :--- |
| 📊 **`chatbot` 구글 시트** | [https://docs.google.com/spreadsheets/d/1lWMlwxRLNi9cHHhJeueMk4zmIXYOCYsJJY7GRZ2deik](https://docs.google.com/spreadsheets/d/1lWMlwxRLNi9cHHhJeueMk4zmIXYOCYsJJY7GRZ2deik) | **매물/FAQ 실시간 입력/수정 문서 (코딩 필요없음)** |
| 🟢 **네이버 톡톡 1:1 대화창** | [https://talk.naver.com/wcse9p](https://talk.naver.com/wcse9p) | 손님용 대화 테스트 및 모니터링 |
| 🟡 **카카오 봇 테스트 직통** | [https://i.kakao.com/bot/6a79752c68acf42eb9657233/action/6a7997c26156d5756309d4a6](https://i.kakao.com/bot/6a79752c68acf42eb9657233/action/6a7997c26156d5756309d4a6) | 카카오 오픈빌더 봇 테스트 직접가기 |
| 🐙 **GitHub 소스 업로드** | [https://github.com/newlbc0-lgtm/chatbot/upload/main](https://github.com/newlbc0-lgtm/chatbot/upload/main) | 파일 업로드 페이지 |
| ☁️ **Render 서버 대시보드** | [https://dashboard.render.com/web/srv-d9tbunu417fc73e1o650](https://dashboard.render.com/web/srv-d9tbunu417fc73e1o650) | 클라우드 서버 관리 |

---

## 3. 주요 소스 파일 및 구조

* **`google_sheets.py`** ([google_sheets.py](file:///d:/python-prg/chatbot/google_sheets.py)): 
  * 사장님의 `chatbot` 구글 시트 데이터를 실시간 직접 API 연결하여 읽어오는 핵심 연동 모듈
* **`main.py`** ([main.py](file:///d:/python-prg/chatbot/main.py)): 
  * 구글 시트 실시간 데이터와 Claude AI 결합 응답
  * 카카오톡 웹훅 (`POST /kakao/webhook`) & 네이버 톡톡 웹훅 (`POST /naver/webhook`)
* **`knowledge_base.py`** ([knowledge_base.py](file:///d:/python-prg/chatbot/knowledge_base.py)): 부동산 기본 지식 및 AI 시스템 프롬프트
