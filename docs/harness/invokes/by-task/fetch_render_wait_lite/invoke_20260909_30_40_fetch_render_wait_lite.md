# Invoke 留档 · 30+40 · fetch_render_wait_lite

- **task**：`docs/tasks/active/task_fetch_render_wait_lite.md`
- **hats**：30（执行编码）+ 40（自检，同上下文闭环）
- **分支 / 工作区**：`task/fetch_render_wait_lite` · `.worktrees/fetch`
- **解释器**：`/Users/cyning/Desktop/grab_web_agent/.venv/bin/python`

## 人工闸扫描（GATE_VERIFY · 首输出）

| human_gate_id | task表status | 用户/invoke声称 | 一致？ | blocks_30 | 30可开工？ |
|---------------|--------------|-----------------|--------|-----------|------------|
| HG-TASK-DRAFT | approved | 派发 Prompt 称已签 | Y | Y（22-R1,30） | — |
| HG-AUDIT-R1 | approved | 派发 Prompt 称已签 | Y | Y | ✅ 可 30 |

- 机械校验：`npx --yes dsh-coding-kit@1.10.0 verify --task docs/tasks/active/task_fetch_render_wait_lite.md`
  - 首跑 **VERIFY: BLOCKED · missing pre-30 invoke hats: 10**（hat-10 invoke 留档在主仓根、未同步进本 worktree）→ 从主仓同步 `invoke_20260909_10_fetch_render_wait_lite.md` 后复跑 → **VERIFY: PASS**（exit 0）
- 结论：**可进入读码/改码**。

## 30 实施摘要

| 改动 | 落点 | 要点 |
|------|------|------|
| 渲染完成确认 | `app/services/acquisition/browser.py` | goto(domcontentloaded) 后 `_wait_for_render`：networkidle 优先（`FETCH_RENDER_TIMEOUT_MS`，默认 10000，模块内 os.getenv · config.py 冻结未动）→ 超时降级 domcontentloaded 兜底 → 非占位文本等待（`wait_for_function`：body innerText 剔除空白与 `-—–_` 占位符后 ≥30 字符）；非占位等待超时 → FetchTimeout 终态，确认通过前不调用 `page.content()` |
| 滑块/验证码检出 | `browser.py _detect_anti_bot` | 三级：① HTTP 401/403 + title/URL 特征（既有）；② 主框架 innerText/raw_dom 滑块文案与组件签名（拖动下方滑块完成拼图 / nc-container / geetest 等）；③ **子框架补扫**：`page.frames[1:]` URL 特征（websitecaptcha/slidervalid）+ 子框架正文 —— 真机实证东财滑块挂独立 iframe（`i.eastmoney.com/websitecaptcha/slidervalid`），主框架 DOM/正文均不可见，首版实现漏检（截图含滑块却放行解析），补扫修复；命中即 anti_bot_flag → 图内 ANTI_BOT 终态 + 截图留痕 + 跳过 bbox 采集，禁止解析半成品 |
| 默认 URL 切换 | `.env.example` / `README.md` / `docs/spec/architecture/frontend_backend_breakdown_v1.md` | TASK_TARGET_URLS → concept/sz000858 + concept/sz300810；README 新增演示 URL 行 ×2 + 已知事项第 2 条改写（等待锚点已落地）；架构 §5 D4 补修订注 + 修订记录一行 |
| 旧测处置（验收 grep 影响面 10 文件 26 处） | tests/ | 改：`test_web_console_sse.py` TARGET_URL → concept；`test_web_console_api.py` ×2 → concept；`test_acquisition_pipeline.py` live 冒烟 URL → concept（维持默认 skipped，不参数化以钉死 collected 口径）；保留：mock 失败注入（URL 仅参数 · SSRF/失败注入语义）/ test_acquisition_url 白名单 / internal_rag 全组 / parser fixture / chunker 纯字符串 |
| 新增单测 | `tests/test_acquisition_browser.py` ×10 | 渲染等待：networkidle 优先断言 / 兜底链断言 / 非占位文本超时 → FetchTimeout 且不放行 content() / env 覆盖；滑块：主框架文案检出 / 图级 ANTI_BOT 终态闭环（无 payload 无 blocks）/ **iframe URL 检出** / **iframe 正文检出** / 正常 fixture 不误报 / 广告 iframe 不误报；全程 FakePage + monkeypatch sync_playwright，零真实浏览器/外网 |

## 40 自检（同上下文闭环）

| 命令 | 退出码 | 结果 |
|------|--------|------|
| `npx --yes dsh-coding-kit@1.10.0 verify --task <task>` | 0 | **VERIFY: PASS**（首跑 BLOCKED·缺 hat-10 invoke，同步后 PASS） |
| `.venv/bin/python -m pytest tests --collect-only -q` | 0 | **116 collected**（基线 106 + 新增 10） |
| `.venv/bin/python -m pytest tests -q` | 0 | **114 passed, 2 skipped**（基线 104+2 → 114+2，零回退、skipped 无新增失败） |
| `npx --yes dsh-coding-kit@1.10.0 task lint-wiki-delta --target .` | 0 | **LINT-WIKI-DELTA: PASS** |
| 真机复跑（NO_PROXY 净化 · uvicorn :8011 · POST /api/task + SSE） | — | 见 task 实现备忘「真机复跑结果」行 |

验收逐条对照与已知未测项已回填 task `### 自检结论（执行者）`；实现备忘三行已回填。验收勾选框未动（留 00 验收）。

## 共享改动申报

- `app/config.py` **未动**（冻结遵守）；新 env `FETCH_RENDER_TIMEOUT_MS`（默认 10000）在 browser.py 模块内 os.getenv 读取——**建议后续在 .env.example 补录该变量注释行**（本 task 仅放行 TASK_TARGET_URLS 行改动，未擅自加）。
- 改动 `docs/spec/architecture/frontend_backend_breakdown_v1.md`（task 范围第 3 行「架构文档决策记录补 D4 修订注」明文放行）。
- 未动：app/services/rag/** · app/api/** · app/web/** · internal_rag.py · supervisor.py · requirements.txt · 其他图文件。

## 阻塞/风险

- 东财当前对本机 IP 持续下发滑块（concept 双链 + 探针共 5 连命中）；检出语义已实机验证（ANTI_BOT 终态 + SSE error + 截图留痕），「干净 Done + 无滑块截图」以冷却后末次重试结果为准，详见 task 实现备忘。
