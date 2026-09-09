"""LangGraph 图骨架包：supervisor 主控图 + acquisition / internal_rag 双子图。

全部节点为 stub（task_project_scaffold 非范围首行）：无任何真实抓取/解析/检索/LLM 调用，
实现属下游 task_web_acquisition_subgraph / task_internal_rag_subgraph。
"""
