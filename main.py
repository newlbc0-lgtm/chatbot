from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="KakaoTalk Chatbot Server",
    description="FastAPI Backend for Kakao i Open Builder Webhook Integration",
    version="1.0.0",
)

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

# -----------------------------------------------------------------------------
# Helper Functions for Kakao Response Generation (v2.0)
# -----------------------------------------------------------------------------
def build_simple_text_response(text: str, quick_replies: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    카카오 챗봇 기본 SimpleText 응답 페이로드를 생성합니다.
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
    테스트용 홈 화면 엔드포인트
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>카카오 챗봇 서버 상태</title>
        <link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-color: #0f172a;
                --card-bg: #1e293b;
                --accent-yellow: #FEE500;
                --text-main: #f8fafc;
                --text-sub: #94a3b8;
                --success: #10b981;
            }
            body {
                font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
                background-color: var(--bg-color);
                color: var(--text-main);
                margin: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }
            .container {
                background: var(--card-bg);
                border: 1px solid #334155;
                border-radius: 20px;
                padding: 40px;
                max-width: 600px;
                width: 90%;
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
            }
            .badge {
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
            }
            .pulse-dot {
                width: 8px;
                height: 8px;
                background-color: var(--success);
                border-radius: 50%;
                box-shadow: 0 0 10px var(--success);
            }
            h1 {
                margin: 0 0 10px 0;
                font-size: 1.8rem;
                font-weight: 800;
            }
            p {
                color: var(--text-sub);
                line-height: 1.6;
                margin: 0 0 25px 0;
            }
            .endpoint-card {
                background: #0f172a;
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 16px;
                border: 1px solid #334155;
            }
            .method {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 6px;
                font-weight: 700;
                font-size: 0.75rem;
                margin-right: 8px;
            }
            .method.post { background: #ea580c; color: white; }
            .method.get { background: #2563eb; color: white; }
            .url {
                font-family: monospace;
                color: var(--accent-yellow);
                font-size: 0.95rem;
            }
            .footer {
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #334155;
                font-size: 0.85rem;
                color: var(--text-sub);
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="badge">
                <span class="pulse-dot"></span> Server Active
            </div>
            <h1>🤖 카카오톡 챗봇 백엔드 서버</h1>
            <p>FastAPI 기반의 카카오 i 오픈빌더 웹훅 서버가 정상적으로 동작 중입니다.</p>

            <div class="endpoint-card">
                <div><span class="method post">POST</span><span class="url">/kakao/webhook</span></div>
                <p style="margin: 8px 0 0 0; font-size: 0.85rem;">카카오 오픈빌더 스킬 웹훅 수신 전용 엔드포인트</p>
            </div>

            <div class="endpoint-card">
                <div><span class="method get">GET</span><span class="url">/docs</span></div>
                <p style="margin: 8px 0 0 0; font-size: 0.85rem;">Swagger 대화형 API 문서 확인</p>
            </div>

            <div class="footer">
                FastAPI Chatbot Backend &bull; Cloudflare Tunnel Ready
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/kakao/webhook")
async def kakao_webhook(request: Request):
    """
    카카오 i 오픈빌더 웹훅 요청 수신 엔드포인트
    """
    try:
        data = await request.json()
        
        # 발화문 추출 (사용자가 보낸 메시지)
        user_utterance = data.get("userRequest", {}).get("utterance", "")
        bot_id = data.get("bot", {}).get("name", "챗봇")

        print(f"[Kakao Webhook Received] Utterance: '{user_utterance}' | Bot: '{bot_id}'")

        # 챗봇 응답 메시지 생성
        reply_text = (
            f"안녕하세요! 카카오톡 챗봇입니다. 🤖\n\n"
            f"보내주신 메시지: \"{user_utterance}\"\n\n"
            f"서버가 정상적으로 응답하고 있습니다."
        )

        # 자주 묻는 질문/바로가기 버튼 예시 (Quick Replies)
        quick_replies = [
            {
                "label": "도움말",
                "action": "message",
                "messageText": "도움말"
            },
            {
                "label": "서버 상태",
                "action": "message",
                "messageText": "서버 상태 확인"
            }
        ]

        response_body = build_simple_text_response(reply_text, quick_replies=quick_replies)
        return JSONResponse(content=response_body, status_code=200)

    except Exception as e:
        print(f"[Error in kakao_webhook]: {e}")
        # 오류 발생 시 기본 에러 응답 반환
        error_response = build_simple_text_response("요청을 처리하는 도중 에러가 발생했습니다. 잠시 후 다시 시도해 주세요.")
        return JSONResponse(content=error_response, status_code=200)
