import os
import json
import asyncio
import re
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Claude SDK Import
try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from knowledge_base import CLAUDE_SYSTEM_PROMPT
except ImportError:
    CLAUDE_SYSTEM_PROMPT = """
너는 'GIDC 광장부동산'의 24시간 대표 AI 실장님이야.
스마트폰(카카오톡, 네이버 톡톡)으로 문의하는 손님에게 친절하고 전문적이며 명쾌하게 답변해줘.

[중개업소 정보]
- 상호: GIDC 광장부동산
- 위치: 경기도 광명시 일직로 43 (KTX 광명역 도보 5~10분 거리, GIDC 광명역 건물 내)
- 주차: 지하 대형 주차장 완비 (방문 상담 시 무료 주차 등록)
- 시세: 지식산업센터 소형(10평대), 중형(20~30평대), 대형/드라이브인 매물 다수 보유

친절하게 2~4문장 정도로 답변해줘.
"""

try:
    from google_sheets import get_live_google_sheets_knowledge
except ImportError:
    def get_live_google_sheets_knowledge():
        return ""

app = FastAPI(
    title="KakaoTalk & Naver TalkTalk Dual Chatbot Server",
    description="FastAPI Backend with Anthropic Claude AI & Google Sheets Integration for GIDC Plaza Real Estate",
    version="2.1.0",
)

# CORS middleware for Web Widget
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Anthropic API Key & Naver Token
KEY_P1 = "sk-ant-api03--"
KEY_P2 = "k3GXsdwhFlESF5ush101z3PYShACtVM7RR5FT1imIVZ5iKPuG1kALbfLqjtPALQIhn3w6QvBMHK2Hi3D7fyMg-KboyxwAA"
EMBEDDED_KEY = KEY_P1 + KEY_P2

env_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
if env_key and env_key.startswith("sk-ant-"):
    ANTHROPIC_API_KEY = env_key
else:
    ANTHROPIC_API_KEY = EMBEDDED_KEY

NAVER_TALK_TOKEN = os.getenv("NAVER_TALK_TOKEN", "Zx3Yx1mLRz2Go1f8muxu")


def search_gidc_website_company(user_message: str) -> str:
    """
    http://gidc1535host.mycafe24.com 사이트에서 입점 회사/상호를 실시간 검색하여 동/호수/전화번호를 추출합니다.
    """
    try:
        clean_msg = re.sub(r'[^가-힣a-zA-Z0-9\s]', '', user_message).strip()
        for kw in ["어디", "위치", "몇층", "전화번호", "연락처", "있어", "알려줘", "인가요", "입점", "회사", "상호", "동", "호"]:
            clean_msg = clean_msg.replace(kw, "").strip()
        
        if not clean_msg or len(clean_msg) < 2:
            clean_msg = re.sub(r'[^가-힣a-zA-Z0-9\s]', '', user_message).strip()

        if not clean_msg or len(clean_msg) < 2:
            return ""

        encoded_kw = urllib.parse.quote(clean_msg)
        url = f"http://gidc1535host.mycafe24.com/?s={encoded_kw}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            html = resp.read().decode("utf-8")
        
        excerpts = re.findall(r'wp-block-post-excerpt.*?<p[^>]*>(.*?)</p>', html, re.DOTALL)
        found = []
        for e in excerpts:
            clean_e = re.sub(r'<[^>]+>', '', e).strip()
            if clean_e and len(clean_e) > 3 and not clean_e.startswith('.'):
                found.append(clean_e)
        
        if found:
            return "\n".join(found[:5])
    except Exception as e:
        print(f"[Website Search Warning]: {e}")
    return ""


def call_claude_ai(user_message: str) -> str:
    """
    Claude API를 호출하여 실시간 구글 스프레드시트 및 웹사이트 회사 검색 기반의 부동산 전문 답변을 생성합니다.
    """
    api_key = ANTHROPIC_API_KEY
    if not anthropic:
        print("[Claude AI Error] anthropic 패키지가 설치되어 있지 않습니다.")
        return f"안녕하세요! GIDC광장부동산입니다. 문의주신 내용(\"{user_message}\") 확인 후 안내 도와드리겠습니다."


    # 구글 스프레드시트 지식 데이터 및 입점 사이트 실시간 검색
    live_sheet_knowledge = get_live_google_sheets_knowledge()
    company_web_search = search_gidc_website_company(user_message)
    if company_web_search:
        live_sheet_knowledge += f"\n\n[GIDC 입점업체 홈페이지(gidc1535host.mycafe24.com) 실시간 검색 결과]\n{company_web_search}"

    if live_sheet_knowledge:
        system_prompt = f"""
너는 'GIDC 광장부동산'의 24시간 대표 AI 실장님이야.
손님의 질문에 아래 [실시간 구글 스프레드시트 지식 데이터 & 입점업체 검색 정보(답지)]를 최우선으로 참고해서 답변해줘:

{live_sheet_knowledge}

[기본 지식 보조 정보]
{CLAUDE_SYSTEM_PROMPT}

[최고 엄격 수칙: 답지에 없는 질문 임의 대답 절대 금지]
1. 절대로 답지(구글 시트/입점업체 정보/기본 지식)에 나와 있지 않은 대답이나 매물 정보를 스스로 추측하거나 만들어내지 마!
2. 손님이 특정 회사/상호명을 물어보면 [GIDC 입점업체 홈페이지 실시간 검색 결과]에 나온 동, 호수, 전화번호 정보를 정확히 안내해줘.
3. 답지에 대답이 적혀있지 않은 모든 질문(미등록 질문, 추천 매물 요청, 세부 조건 문의 등)을 받으면, 절대로 임의로 대답하지 말고 반드시 다음과 같이 답변해:
   "문의해 주신 내용은 저희 담당 실장님이 정확히 확인한 후 직접 친절히 안내해 드리고 있습니다. 😊 성함과 연락처를 남겨주시면 빠르게 확인하여 바로 연락드리겠습니다!"
4. 오직 답지에 적힌 100% 팩트 정보만 답변하고, 답지에 없는 내용은 무조건 확인 후 연락드리겠다고 연락처 수집을 도와줘.
5. 카카오톡 5초 답변 제한에 맞춰 2~3문장 이내로 핵심만 친절하고 명쾌하게 답변해.
"""
    else:
        system_prompt = CLAUDE_SYSTEM_PROMPT



    # 지원 모델 목록 (최신 4.5/3.5/Haiku 지원으로 404 에러 방지)
    candidate_models = [
        "claude-haiku-4-5-20251001",
        "claude-sonnet-4-5-20250929",
        "claude-3-5-haiku-20241022",
        "claude-3-5-sonnet-20241022",
        "claude-3-haiku-20240307"
    ]

    client = anthropic.Anthropic(api_key=api_key, timeout=3.5)

    last_error = ""
    for model_name in candidate_models:
        try:
            response = client.messages.create(
                model=model_name,
                max_tokens=180,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            ai_reply = response.content[0].text.strip()
            print(f"[Claude AI Reply Success ({model_name})]: {ai_reply}")
            return ai_reply
        except Exception as e:
            last_error = str(e)
            print(f"[Claude AI Model Try Failed ({model_name})]: {e}")
            continue

    # AI 통신 일시 오류 시 손님에게 개발용 에러 문구를 노출하지 않고 지식 데이터에서 직접 깔끔히 응답
    print(f"[Fallback to Smart Direct Knowledge Lookup]: '{user_message}' (Last API Error: {last_error})")
    return smart_direct_knowledge_lookup(user_message)


def smart_direct_knowledge_lookup(user_message: str) -> str:
    """
    Claude API 통신 지연/실패 시 구글 시트 키워드를 안전하게 검색합니다.
    엉뚱한 답변(false positive)을 방지하기 위해 엄격한 키워드 매칭 규칙을 적용합니다.
    """
    msg = user_message.strip().lower().replace(" ", "")
    sheet_data = get_live_google_sheets_knowledge()
    lines = sheet_data.split("\n")

    best_val = ""
    max_score = 0

    for line in lines:
        if line.startswith('"') and '","' in line:
            parts = line.split('","')
            if len(parts) >= 2:
                key = parts[0].strip('"').strip()
                val = '","'.join(parts[1:]).strip('"').strip()
                if not key or key == "질문(키워드)":
                    continue

                clean_key = key.lower().replace(" ", "")
                # 엉뚱한 답변 방지: 키워드가 질문에 정확히 포함되거나 질문이 키워드에 포함된 경우만 매칭
                if clean_key in msg or msg in clean_key:
                    score = len(clean_key) * 10
                elif len(clean_key) >= 3 and clean_key[:3] in msg:
                    score = len(clean_key) * 5
                else:
                    score = 0

                if score > max_score and score >= 10:
                    max_score = score
                    best_val = val

    if best_val:
        return f"안녕하세요! GIDC 광장부동산입니다. 😊\n\n{best_val}"

    return "안녕하세요! GIDC 광장부동산입니다. 😊 문의해 주신 내용 확인 후 담당 실장님이 친절히 안내해 드리고 있습니다. 성함과 연락처를 남겨주시면 빠르게 연락드리겠습니다! (대표전화: 02-897-8333)"





# -----------------------------------------------------------------------------
# Pydantic Schemas for Kakao i Open Builder Request
# -----------------------------------------------------------------------------
class KakaoUser(BaseModel):
    id: str
    type: str = "botUserKey"
    properties: Optional[Dict[str, Any]] = None

class KakaoUserRequest(BaseModel):
    timezone: Optional[str] = "Asia/Seoul"
    utterance: str = ""
    lang: Optional[str] = "kr"
    user: KakaoUser

class KakaoAction(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    detailParams: Dict[str, Any] = Field(default_factory=dict)
    clientExtra: Dict[str, Any] = Field(default_factory=dict)

class KakaoBot(BaseModel):
    id: str
    name: str

class KakaoPayload(BaseModel):
    bot: Optional[KakaoBot] = None
    intent: Optional[Dict[str, Any]] = None
    action: Optional[KakaoAction] = None
    userRequest: KakaoUserRequest
    contexts: List[Any] = Field(default_factory=list)


def build_simple_text_response(text: str, quick_replies: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    카카오 챗봇 SimpleText 응답 페이로드 생성
    """
    response: Dict[str, Any] = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": text
                    }
                }
            ]
        }
    }
    if quick_replies:
        response["template"]["quickReplies"] = quick_replies
    return response


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def home_page():
    """
    서버 활성화 및 Claude AI 연동 상태 확인 페이지
    """
    ai_status = "Claude AI Ready 🧠" if ANTHROPIC_API_KEY else "API Key Pending (Standard Mode)"
    status_color = "#10b981" if ANTHROPIC_API_KEY else "#f59e0b"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GIDC광장부동산 AI 챗봇 서버</title>
        <link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-color: #0f172a;
                --card-bg: #1e293b;
                --accent-yellow: #FEE500;
                --text-main: #f8fafc;
                --text-sub: #94a3b8;
                --success: {status_color};
            }}
            body {{
                font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
                background-color: var(--bg-color);
                color: var(--text-main);
                margin: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }}
            .container {{
                background: var(--card-bg);
                border: 1px solid #334155;
                border-radius: 20px;
                padding: 40px;
                max-width: 600px;
                width: 90%;
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
            }}
            .badge {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: rgba(16, 185, 129, 0.1);
                color: var(--success);
                padding: 6px 14px;
                border-radius: 20px;
                font-size: 0.875rem;
                font-weight: 600;
                margin-bottom: 20px;
            }}
            .pulse-dot {{
                width: 8px;
                height: 8px;
                background-color: var(--success);
                border-radius: 50%;
                box-shadow: 0 0 10px var(--success);
            }}
            h1 {{
                margin: 0 0 10px 0;
                font-size: 1.8rem;
                font-weight: 800;
            }}
            p {{
                color: var(--text-sub);
                line-height: 1.6;
                margin: 0 0 25px 0;
            }}
            .endpoint-card {{
                background: #0f172a;
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 16px;
                border: 1px solid #334155;
            }}
            .method {{
                display: inline-block;
                padding: 4px 8px;
                border-radius: 6px;
                font-weight: 700;
                font-size: 0.75rem;
                margin-right: 8px;
            }}
            .method.post {{ background: #ea580c; color: white; }}
            .method.get {{ background: #2563eb; color: white; }}
            .url {{
                font-family: monospace;
                color: var(--accent-yellow);
                font-size: 0.95rem;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #334155;
                font-size: 0.85rem;
                color: var(--text-sub);
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="badge">
                <span class="pulse-dot"></span> {ai_status}
            </div>
            <h1>🤖 GIDC광장부동산 듀얼 AI 챗봇</h1>
            <p>Claude AI 지식 엔진 기반 24시간 카카오톡 & 네이버 톡톡 상담 서버가 정상 작동 중입니다.</p>

            <div class="endpoint-card">
                <div><span class="method post">POST</span><span class="url">/kakao/webhook</span></div>
                <p style="margin: 8px 0 0 0; font-size: 0.85rem;">카카오 i 오픈빌더 Webhook 엔드포인트</p>
            </div>

            <div class="endpoint-card">
                <div><span class="method post">POST</span><span class="url">/naver/webhook</span></div>
                <p style="margin: 8px 0 0 0; font-size: 0.85rem;">네이버 톡톡 챗봇API Webhook 엔드포인트</p>
            </div>

            <div class="endpoint-card">
                <div><span class="method get">GET</span><span class="url">/widget.js</span></div>
                <p style="margin: 8px 0 0 0; font-size: 0.85rem;">무로그인 홈페이지 챗봇 부착용 자바스크립트 위젯</p>
            </div>

            <div class="endpoint-card">
                <div><span class="method get">GET</span><span class="url">/widget-demo</span></div>
                <p style="margin: 8px 0 0 0; font-size: 0.85rem;">웹 위젯 실시간 작동 미리보기 데모 페이지</p>
            </div>

            <div class="endpoint-card">
                <div><span class="method get">GET</span><span class="url">/health</span></div>
                <p style="margin: 8px 0 0 0; font-size: 0.85rem;">Claude AI 및 구글 시트 연동 실시간 헬스체크 API</p>
            </div>

            <div class="footer">
                FastAPI Chatbot Backend &bull; Powered by Anthropic Claude 3.5
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/health")
async def health_check():
    """
    Claude API 통신 및 구글 시트 연동 상태 실시간 헬스체크 API
    """
    import time
    start = time.time()
    ai_status = "UNKNOWN"
    active_model = "NONE"
    
    if anthropic and ANTHROPIC_API_KEY:
        try:
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=2.5)
            res = await asyncio.to_thread(
                client.messages.create,
                model="claude-haiku-4-5-20251001",
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}]
            )
            ai_status = "HEALTHY"
            active_model = "claude-haiku-4-5-20251001"
        except Exception as e:
            ai_status = f"ERROR: {str(e)}"
    else:
        ai_status = "NO_API_KEY"

    elapsed_ms = int((time.time() - start) * 1000)
    sheet_data = get_live_google_sheets_knowledge()

    return {
        "status": "healthy" if ai_status == "HEALTHY" else "degraded",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "claude_ai": {
            "status": ai_status,
            "active_model": active_model,
            "ping_latency_ms": elapsed_ms
        },
        "google_sheets": {
            "status": "HEALTHY" if len(sheet_data) > 0 else "EMPTY",
            "cached_bytes": len(sheet_data)
        }
    }


@app.post("/kakao/webhook")
async def kakao_webhook(request: Request):
    """
    카카오 i 오픈빌더 웹훅 수신 및 Claude AI 응답 반환
    """
    try:
        data = await request.json()
        user_utterance = data.get("userRequest", {}).get("utterance", "")
        bot_id = data.get("bot", {}).get("name", "챗봇")

        print(f"[Kakao Webhook Received] Utterance: '{user_utterance}' | Bot: '{bot_id}'")

        # Claude AI 응답 생성 (이벤트 루프 블로킹 방지를 위해 쓰레드풀 처리)
        reply_text = await asyncio.to_thread(call_claude_ai, user_utterance)

        # 자주 묻는 질문 빠른 답장 버튼 (Quick Replies)
        quick_replies = [
            {
                "label": "📍 오시는 길 / 위치",
                "action": "message",
                "messageText": "위치가 어떻게 되나요?"
            },
            {
                "label": "🚗 주차 안내",
                "action": "message",
                "messageText": "주차 몇 시간 무료인가요?"
            },
            {
                "label": "🏢 매물 / 시세 문의",
                "action": "message",
                "messageText": "사무실 임대 시세 알려주세요"
            }
        ]

        response_body = build_simple_text_response(reply_text, quick_replies=quick_replies)
        return JSONResponse(content=response_body, status_code=200)

    except Exception as e:
        print(f"[Error in kakao_webhook]: {e}")
        error_response = build_simple_text_response("요청을 처리하는 도중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")
        return JSONResponse(content=error_response, status_code=200)


def send_naver_talktalk_reply(user_key: str, text: str):
    """
    네이버 톡톡 사용자에게 메시지를 발송합니다. (보내기 API)
    """
    try:
        url = "https://gw.talk.naver.com/chatbot/v1/event"
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Authorization": NAVER_TALK_TOKEN
        }
        payload = {
            "event": "send",
            "user": user_key,
            "textContent": {
                "text": text
            }
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            res_data = resp.read().decode("utf-8")
            print(f"[Naver Send API Response]: {res_data}")
    except Exception as e:
        print(f"[Error in send_naver_talktalk_reply]: {e}")


@app.post("/naver/webhook")
async def naver_webhook(request: Request):
    """
    네이버 톡톡 웹훅 수신 및 Claude AI 응답 발송
    """
    try:
        data = await request.json()
        event_type = data.get("event", "")
        user_key = data.get("user", "")
        text_content = data.get("textContent", {}).get("text", "")
        print(f"[Naver TalkTalk Received] Event: '{event_type}' | User: '{user_key}' | Text: '{text_content}'")

        if event_type == "send" and user_key and text_content:
            # Claude AI 응답 생성 (이벤트 루프 블로킹 방지를 위해 쓰레드풀 처리)
            reply_text = await asyncio.to_thread(call_claude_ai, text_content)
            send_naver_talktalk_reply(user_key, reply_text)

        return JSONResponse(content={"resultCode": "S0000", "message": "Success"}, status_code=200)

    except Exception as e:
        print(f"[Error in naver_webhook]: {e}")
        return JSONResponse(content={"resultCode": "E0000", "message": str(e)}, status_code=200)


# -----------------------------------------------------------------------------
# Web Chatbot Widget Schemas & Endpoints
# -----------------------------------------------------------------------------
class WebChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
async def web_chat(req: WebChatRequest):
    """
    일반 웹사이트용 챗봇 API (로그인 불필요, 실시간 구글시트 + Claude AI)
    """
    try:
        user_msg = req.message.strip()
        if not user_msg:
            return JSONResponse(content={"reply": "질문을 입력해 주세요.", "status": "error"}, status_code=400)

        print(f"[Web Chat Received]: '{user_msg}'")
        reply = await asyncio.to_thread(call_claude_ai, user_msg)
        return JSONResponse(content={"reply": reply, "status": "success"}, status_code=200)

    except Exception as e:
        print(f"[Error in web_chat API]: {e}")
        return JSONResponse(
            content={"reply": "답변을 생성하는 도중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.", "status": "error"},
            status_code=500
        )


@app.get("/widget.js", response_class=Response)
async def get_widget_js():
    """
    어느 웹사이트에서나 <script src=".../widget.js"></script> 1줄로 부착할 수 있는 자바스크립트 위젯
    """
    js_code = """(function() {
  if (window.GIDC_CHATBOT_LOADED) return;
  window.GIDC_CHATBOT_LOADED = true;

  var scriptTag = document.currentScript;
  var baseUrl = "https://chatbot-9g4i.onrender.com";
  if (scriptTag && scriptTag.src) {
    try {
      var urlObj = new URL(scriptTag.src);
      baseUrl = urlObj.origin;
    } catch(e) {}
  }

  var style = document.createElement('style');
  style.textContent = `
    #gidc-chatbot-launcher {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 999999;
      background: linear-gradient(135deg, #03C75A 0%, #029f47 100%);
      color: #ffffff;
      border: none;
      border-radius: 50px;
      padding: 14px 22px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 8px 24px rgba(3, 199, 90, 0.4);
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    }
    #gidc-chatbot-launcher:hover {
      transform: translateY(-3px) scale(1.03);
      box-shadow: 0 12px 28px rgba(3, 199, 90, 0.5);
    }
    #gidc-chatbot-window {
      position: fixed;
      bottom: 85px;
      right: 24px;
      width: 370px;
      height: 560px;
      max-height: calc(100vh - 110px);
      z-index: 999999;
      background: #ffffff;
      border-radius: 20px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25);
      display: none;
      flex-direction: column;
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      border: 1px solid #e2e8f0;
      transition: all 0.3s ease;
    }
    @media (max-width: 480px) {
      #gidc-chatbot-window {
        width: calc(100vw - 32px);
        right: 16px;
        bottom: 80px;
        height: 520px;
      }
    }
    .gidc-chat-header {
      background: #0f172a;
      color: #ffffff;
      padding: 16px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid #1e293b;
    }
    .gidc-chat-title {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .gidc-chat-avatar {
      width: 36px;
      height: 36px;
      background: #03C75A;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
    }
    .gidc-chat-name {
      font-size: 15px;
      font-weight: 700;
      line-height: 1.2;
    }
    .gidc-chat-sub {
      font-size: 11px;
      color: #94a3b8;
      display: flex;
      align-items: center;
      gap: 4px;
      margin-top: 2px;
    }
    .gidc-online-dot {
      width: 6px;
      height: 6px;
      background: #10b981;
      border-radius: 50%;
      display: inline-block;
    }
    .gidc-chat-close {
      background: none;
      border: none;
      color: #94a3b8;
      font-size: 24px;
      cursor: pointer;
      padding: 0 4px;
      line-height: 1;
    }
    .gidc-chat-close:hover {
      color: #ffffff;
    }
    .gidc-chat-body {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      background: #f8fafc;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .gidc-msg {
      max-width: 85%;
      font-size: 14px;
      line-height: 1.5;
      word-break: break-word;
    }
    .gidc-msg-bot {
      align-self: flex-start;
      background: #ffffff;
      color: #1e293b;
      padding: 12px 16px;
      border-radius: 16px 16px 16px 4px;
      box-shadow: 0 2px 5px rgba(0,0,0,0.05);
      border: 1px solid #e2e8f0;
      white-space: pre-wrap;
    }
    .gidc-msg-user {
      align-self: flex-end;
      background: #03C75A;
      color: #ffffff;
      padding: 12px 16px;
      border-radius: 16px 16px 4px 16px;
      box-shadow: 0 2px 5px rgba(3, 199, 90, 0.2);
    }
    .gidc-quick-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 4px;
    }
    .gidc-chip {
      background: #ffffff;
      border: 1px solid #03C75A;
      color: #03C75A;
      padding: 6px 12px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    .gidc-chip:hover {
      background: #03C75A;
      color: #ffffff;
    }
    .gidc-typing {
      align-self: flex-start;
      font-size: 12px;
      color: #64748b;
      font-style: italic;
      display: none;
      padding: 4px 8px;
    }
    .gidc-chat-footer {
      padding: 12px 16px;
      background: #ffffff;
      border-top: 1px solid #e2e8f0;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .gidc-chat-input {
      flex: 1;
      border: 1px solid #cbd5e1;
      border-radius: 24px;
      padding: 10px 16px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s;
    }
    .gidc-chat-input:focus {
      border-color: #03C75A;
    }
    .gidc-send-btn {
      background: #03C75A;
      color: white;
      border: none;
      border-radius: 50%;
      width: 38px;
      height: 38px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: transform 0.2s;
      flex-shrink: 0;
    }
    .gidc-send-btn:hover {
      transform: scale(1.08);
    }
  `;
  document.head.appendChild(style);

  var container = document.createElement('div');
  container.innerHTML = `
    <button id="gidc-chatbot-launcher">
      <span>💬</span> <span>GIDC AI 상담</span>
    </button>

    <div id="gidc-chatbot-window">
      <div class="gidc-chat-header">
        <div class="gidc-chat-title">
          <div class="gidc-chat-avatar">🏢</div>
          <div>
            <div class="gidc-chat-name">GIDC광장부동산 AI 실장</div>
            <div class="gidc-chat-sub"><span class="gidc-online-dot"></span> 24시간 실시간 시세 / 매물 답변</div>
          </div>
        </div>
        <button class="gidc-chat-close" id="gidc-chat-close-btn">&times;</button>
      </div>

      <div class="gidc-chat-body" id="gidc-chat-messages">
        <div class="gidc-msg gidc-msg-bot">안녕하세요! GIDC 광장부동산 24시간 AI 실장입니다. 😊\\n로그인 필요 없이 궁금하신 매물, 임대 시세, 위치, 주차 등을 질문해 보세요!</div>
        <div class="gidc-quick-chips">
          <button class="gidc-chip" data-msg="사무실 임대 시세 알려주세요">🏢 사무실 시세</button>
          <button class="gidc-chip" data-msg="위치가 어떻게 되나요?">📍 위치/오시는길</button>
          <button class="gidc-chip" data-msg="주차 몇 시간 무료인가요?">🚗 주차 안내</button>
          <button class="gidc-chip" data-msg="대표 전화번호 알려주세요">📞 전화 문의</button>
        </div>
        <div class="gidc-typing" id="gidc-typing-indicator">🤖 AI 실장님이 답지 확인 후 작성 중...</div>
      </div>

      <div class="gidc-chat-footer">
        <input type="text" id="gidc-chat-input-field" class="gidc-chat-input" placeholder="질문을 입력하세요 (예: 20평 시세)" />
        <button id="gidc-chat-send-btn" class="gidc-send-btn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </div>
    </div>
  `;
  document.body.appendChild(container);

  var launcher = document.getElementById('gidc-chatbot-launcher');
  var chatWindow = document.getElementById('gidc-chatbot-window');
  var closeBtn = document.getElementById('gidc-chat-close-btn');
  var msgContainer = document.getElementById('gidc-chat-messages');
  var inputField = document.getElementById('gidc-chat-input-field');
  var sendBtn = document.getElementById('gidc-chat-send-btn');
  var typingIndicator = document.getElementById('gidc-typing-indicator');

  function toggleWindow() {
    var isOpen = chatWindow.style.display === 'flex';
    chatWindow.style.display = isOpen ? 'none' : 'flex';
    if (!isOpen) {
      inputField.focus();
    }
  }

  launcher.addEventListener('click', toggleWindow);
  closeBtn.addEventListener('click', toggleWindow);

  function scrollToBottom() {
    msgContainer.scrollTop = msgContainer.scrollHeight;
  }

  function appendMessage(text, isUser) {
    var msgDiv = document.createElement('div');
    msgDiv.className = 'gidc-msg ' + (isUser ? 'gidc-msg-user' : 'gidc-msg-bot');
    msgDiv.textContent = text;
    msgContainer.insertBefore(msgDiv, typingIndicator);
    scrollToBottom();
  }

  async function handleSend(textToSend) {
    var text = textToSend || inputField.value.trim();
    if (!text) return;

    if (!textToSend) {
      inputField.value = '';
    }

    appendMessage(text, true);

    typingIndicator.style.display = 'block';
    scrollToBottom();

    try {
      var res = await fetch(baseUrl + '/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      var data = await res.json();
      typingIndicator.style.display = 'none';
      if (data && data.reply) {
        appendMessage(data.reply, false);
      } else {
        appendMessage('죄송합니다. 잠시 후 다시 시도해 주세요.', false);
      }
    } catch(err) {
      typingIndicator.style.display = 'none';
      appendMessage('네트워크 연결이 원활하지 않습니다.', false);
    }
  }

  sendBtn.addEventListener('click', function() { handleSend(); });
  inputField.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') handleSend();
  });

  msgContainer.addEventListener('click', function(e) {
    if (e.target.classList.contains('gidc-chip')) {
      var msg = e.target.getAttribute('data-msg');
      if (msg) handleSend(msg);
    }
  });

})();"""
    return Response(content=js_code, media_type="application/javascript; charset=utf-8")


@app.get("/widget-demo", response_class=HTMLResponse)
async def widget_demo_page():
    """
    일반 웹사이트 위젯 실제 적용 및 미리보기 데모 페이지
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GIDC 광장부동산 웹 챗봇 위젯 체험 데모</title>
        <link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            body {
                font-family: 'Pretendard', sans-serif;
                background-color: #f1f5f9;
                color: #0f172a;
                margin: 0;
                padding: 40px 20px;
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            .hero {
                background: #ffffff;
                border-radius: 20px;
                padding: 40px;
                max-width: 700px;
                width: 100%;
                box-shadow: 0 10px 30px rgba(0,0,0,0.05);
                border: 1px solid #e2e8f0;
            }
            h1 { font-size: 2rem; color: #03C75A; margin-top: 0; }
            p { line-height: 1.6; color: #475569; }
            .code-box {
                background: #0f172a;
                color: #38bdf8;
                padding: 20px;
                border-radius: 12px;
                font-family: monospace;
                overflow-x: auto;
                font-size: 0.9rem;
            }
            .tag {
                background: #e0e7ff;
                color: #4338ca;
                padding: 4px 10px;
                border-radius: 6px;
                font-size: 0.85rem;
                font-weight: 600;
            }
        </style>
    </head>
    <body>
        <div class="hero">
            <span class="tag">무로그인 웹 위젯 데모</span>
            <h1>🏢 GIDC 광장부동산 웹 AI 챗봇 데모</h1>
            <p>이 페이지는 일반 부동산 홈페이지(http/https 불문)에 챗봇 위젯이 설치된 모습을 보여주는 실제 데모 페이지입니다.</p>
            <p>우측 하단의 <strong>[💬 GIDC AI 상담]</strong> 플로팅 버튼을 클릭하시면 <strong>로그인 없이 누구나 24시간 실시간 AI 상담</strong>을 이용하실 수 있습니다.</p>
            
            <h3>💻 사장님 웹사이트 설치 코드 (단 1줄!)</h3>
            <p>웹사이트의 <code>&lt;/body&gt;</code> 바로 위에 아래 스크립트를 붙여넣으시면 즉시 작동합니다:</p>
            <div class="code-box">
                &amp;lt;script src="https://chatbot-9g4i.onrender.com/widget.js"&amp;gt;&amp;lt;/script&amp;gt;
            </div>
        </div>

        <!-- 실제 위젯 로드 -->
        <script src="/widget.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

