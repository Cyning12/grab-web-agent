"""Flask 进程入口：仅交付首屏 HTML 骨架，不含任何 /api/* 路由（架构 §0/§2.1）。

启动：flask --app app.web.app run --port $FLASK_PORT
"""

from flask import Flask, render_template

app = Flask(__name__)


@app.get("/")
def index() -> str:
    """首屏模板（task_project_scaffold 验收 · 冒烟断言②）。"""
    return render_template("index.html")
