# invoke 留档 · hat 30+40 · screenshot_delay

| 项 | 值 |
|----|-----|
| hat | 30-execute + 40-self-check（同上下文闭环） |
| task_slug | screenshot_delay |
| 日期 | 2026-09-09 |
| 分支 | task/screenshot_delay（worktree .worktrees/shot） |

## GATE_VERIFY（首输出）

- `npm_config_cache=/tmp/npm-cache-dsh npx --yes dsh-coding-kit@1.10.0 verify --task docs/tasks/active/task_screenshot_delay.md` → **VERIFY: PASS**（HG-TASK-DRAFT approved · HG-AUDIT-R1 approved，均 blocks_30 已签；pre-30 invoke hats 齐全）。

## 过程

1. **读码**：browser.py 截图触发点位于渲染确认探针裁决之后；基线 pytest 122 collected（120+2）亲验吻合。
2. **施工**（task 验收节为准）：
   - browser.py：__init__ 增 `screenshot_delay_ms`（与 FETCH_RENDER_TIMEOUT_MS 同口径模块内 os.getenv + 默认值 5000）；非法值（非数字/负数）落默认 + warning；截图前插点 **条件化**——仅 `not anti_bot` 路径 `page.wait_for_timeout(screenshot_delay_ms)`，anti_bot 终态页仅留痕不空等（20 审观察项② 强制项）。
   - .env.example：补录 `SCREENSHOT_DELAY_MS=5000`（语义 + 推荐值注释）。
   - tests/test_acquisition_browser.py：+TestScreenshotDelay 7 条（env 取值/先于截图/非法值落默认+warning×2/未设走默认/anti_bot 与硬反爬无空等/D7 降级路径同样延迟）。
3. **验证**：pytest 全量 **127 passed + 2 skipped**（基线不回退）；lint-wiki-delta PASS。
4. **真机复跑**：uvicorn 端口 8011（NO_PROXY/no_proxy 大小写双写）→ concept/sz000858 全管道 Pending→Fetching→warning PAGE_CAPTCHA_OVERLAY→Parsing→RAGing→**Done**；task_id=36044d85862a4874b36a0e9e2ec11626；工单号 MOCK-805D21EE；截图 app/static/shot_8b1b8439f2_1788961145303.png（2.1MB 全页渲染完整，顶部仅余小滑块弹窗，供 00 人工看图）。
5. **40 自检**：逐条对照验收（证据回填 task 自检结论节），命令全绿，验收勾选框未动（留 00/维护者签）。

## notes

- 默认值 5000ms 实测依据：东财对本机持续下发滑块，延迟只改善不根除（R5 residual ①），取建议区间上限一档实测，截图主体稳定可判读。
- 边界遵守：仅动 app/services/acquisition/browser.py · tests/test_acquisition_browser.py · .env.example · task 文件 · 本 invoke；config.py/requirements.txt/rag/api/web/supervisor 未碰。
