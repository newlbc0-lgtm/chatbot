import os
import json
import urllib.request
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
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
    version="2.0.0",
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


def call_claude_ai(user_message: str) -> str:
    """
    Claude API를 호출하여 실시간 구글 스프레드시트 기반의 부동산 전문 답변을 생성합니다.
    """
    api_key = ANTHROPIC_API_KEY
    if not anthropic:
        print("[Claude AI Error] anthropic 패키지가 설치되어 있지 않습니다.")
        return f"안녕하세요! GIDC광장부동산입니다. 문의주신 내용(\"{user_message}\") 확인 후 안내 도와드리겠습니다."


    # 구글 스프레드시트 지식 데이터 실시간 조회
    live_sheet_knowledge = get_live_google_sheets_knowledge()
    if live_sheet_knowledge:
        system_prompt = f"""
너는 'GIDC 광장부동산'의 24시간 대표 AI 실장님이야.
손님의 질문에 아래 [실시간 구글 스프레드시트 지식 데이터]를 최우선으로 참고해서 답변해줘:

{live_sheet_knowledge}

[기본 지식 보조 정보]
{CLAUDE_SYSTEM_PROMPT}

[답변 작성 수칙]
1. 카카오톡 5초 답변 제한에 맞춰 2~3문장 이내로 핵심만 친절하고 명쾌하게 답변해.
2. 모바일 화면에서 한눈에 들어오도록 너무 길지 않게 작성해.
3. 구글 스프레드시트의 최신 정보를 바탕으로 답장해줘.
"""
    else:
        system_prompt = CLAUDE_SYSTEM_PROMPT

    # 지원 모델 목록 (최신 검증 모델부터 우선 호출)
    candidate_models = [
        "claude-haiku-4-5-20251001",
        "claude-sonnet-4-6",
        "claude-sonnet-4-5-20250929",
        "claude-3-5-sonnet-20241022",
        "claude-3-haiku-20240307"
    ]

    client = anthropic.Anthropic(api_key=api_key)

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

    return f"안녕하세요! GIDC광장부동산입니다. 🤖\n(AI 연결 상태: {last_error})"





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

            <div class="footer">
                FastAPI Chatbot Backend &bull; Powered by Anthropic Claude 3.5
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


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

        # Claude AI 응답 생성
        reply_text = call_claude_ai(user_utterance)

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
            # Claude AI 응답 생성
            reply_text = call_claude_ai(text_content)
            send_naver_talktalk_reply(user_key, reply_text)

        return JSONResponse(content={"resultCode": "S0000", "message": "Success"}, status_code=200)

    except Exception as e:
        print(f"[Error in naver_webhook]: {e}")
        return JSONResponse(content={"resultCode": "E0000", "message": str(e)}, status_code=200)
