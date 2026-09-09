"""Flask 进程入口：仅交付首屏 HTML 骨架，不含任何 /api/* 路由（架构 §0/§2.1 拓扑钉死）。

- 模板按 ?role=admin 做界面层角色视图（SPEC 范围 5 · 无认证安全语义）；
- 页面内 vanilla JS（fetch / EventSource）直连 FastAPI 进程（api_base 注入模板）。

启动：flask --app app.web.app run --port $FLASK_PORT
"""

from flask import Flask, render_template, request

from app import config

app = Flask(__name__)


@app.get("/")
def index() -> str:
    """首屏模板：输入框 + 按钮 + 三区块骨架 + 底部回执条；admin 视角额外渲染 Step 3。"""
    is_admin = request.args.get("role", "") == "admin"
    api_base = f"http://127.0.0.1:{config.FASTAPI_PORT}"
    return render_template("index.html", is_admin=is_admin, api_base=api_base)
