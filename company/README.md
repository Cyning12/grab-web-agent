# company/ · 内部语料（财报等）目录

> 人决 D6（2026-09-09）+ D6-修订（同日 · 20 审实证裁定）：按**上市编号裸 6 位**命名（`company/000858/`、`company/300810/`）。sz/sh 前缀写法废弃（retriever derive_company_code 剥前缀产出裸号，前缀会致语料分裂）。

## 目录约定

```
company/
  000858/   # 五粮液 —— 巨潮定期报告（抓取脚本自动落盘）
  300810/   # 中科海讯 —— 同上
```

- 语料来源：http://www.cninfo.com.cn 公告查询（抓取脚本：`python -m scripts.fetch_cninfo 000858 300810`，task_cninfo_corpus_scraper 交付）
- 对内子图（Internal RAG）以本目录为「内部知识库」，目录原名即 company_code（V1 本地文件即真值）
- 本目录为数据目录，抓取脚本入参 `sz000858`/`000858` 均归一为裸 6 位
