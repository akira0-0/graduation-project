"""
信息过滤智能体节点
调用数据过滤引擎 API（http://localhost:8081）完成三层过滤：
  Layer-1: 数据库全量读取
  Layer-2: 场景规则过滤
  Layer-3: LLM 相关性过滤

query 推断优先级：
  1. params.query
  2. params.topic
  3. 工作流变量 topic / keyword
  4. params.filters.keywords 拼接
"""
import time
import requests
from typing import Any, Dict, List, Optional

from .base import BaseNode
from ..core.schema import NodeDefinition, WorkflowState
from ..utils.logger import get_logger

logger = get_logger("filter_agent_node")

DEFAULT_FILTER_API_BASE = "http://localhost:8081"
POLL_INTERVAL_S = 3
POLL_TIMEOUT_S  = 300


class FilterAgentNode(BaseNode):
    """
    信息过滤智能体节点（对接数据过滤引擎 API）

    工作流 JSON 兼容格式：
    {
        "id": "data_filter",
        "type": "FilterAgent",
        "config": {
            "params": {
                "query":     "丽江旅游攻略",       // 可选，优先使用
                "platform":  "xhs",               // 可选
                "max_posts": 100,                 // 可选，默认 500
                "filters": {
                    "keywords": ["旅游", "攻略"]   // 无 query 时自动拼接为 query
                },
                "sort_by": "relevance",
                "limit":   15,
                "filter_api_base": "http://localhost:8081"  // 可选
            }
        }
    }
    """

    def __init__(self, node_def: NodeDefinition):
        super().__init__(node_def)

    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        logger.info(f"执行信息过滤智能体节点: {self.node_id}")

        try:
            # ── 读取参数 ──────────────────────────────────────────
            filters     = self.get_input_value(state, "filters") or {}
            limit       = int(self.get_input_value(state, "limit") or 100)
            platform    = self.get_input_value(state, "platform") or None
            max_posts   = int(self.get_input_value(state, "max_posts") or 500)
            api_base    = self.get_input_value(state, "filter_api_base") or DEFAULT_FILTER_API_BASE
            # layer2_mode: relaxed / normal / strict（默认 normal，strict 时额外做关键词过滤）
            layer2_mode = self.get_input_value(state, "layer2_mode") or "normal"

            # ── 推断 query ────────────────────────────────────────
            # 优先级：params.query > params.topic > state.context > filters.keywords
            query = (
                self.get_input_value(state, "query")
                or self.get_input_value(state, "topic")
                or state.context.get("topic")
                or state.context.get("keyword")
                or state.context.get("query")
                or " ".join(filters.get("keywords") or [])
            )

            if not query:
                logger.error("[FilterAgentNode] 无法推断 query，请在 params 中设置 query 字段")
                return self._error_result("query 参数为空，请在节点 params 中设置 query 字段")

            logger.info(f"[FilterAgentNode] query={query!r} platform={platform} max_posts={max_posts} layer2_mode={layer2_mode}")

            # ── Step 1: 异步提交过滤任务 ──────────────────────────
            try:
                session_id = self._start_filter(api_base, query, platform, max_posts, layer2_mode)
            except Exception as e:
                logger.error(f"[FilterAgentNode] 启动过滤失败: {e}")
                return self._error_result(f"调用过滤引擎失败: {e}")

            logger.info(f"[FilterAgentNode] 任务已提交，session_id={session_id}")

            # ── Step 2: 轮询等待完成 ──────────────────────────────
            try:
                stats = self._wait_for_completion(api_base, session_id)
            except Exception as e:
                logger.error(f"[FilterAgentNode] 等待任务失败: {e}")
                return self._error_result(f"过滤任务未完成: {e}")

            logger.info(f"[FilterAgentNode] 过滤完成，stats={stats}")

            # ── Step 3: 获取 L3 结果 ──────────────────────────────
            posts = self._fetch_results(api_base, session_id, limit)

            # ── Step 3b: L3=0 时降级到 L2 ────────────────────────
            fallback_used = False
            if not posts:
                logger.warning(f"[FilterAgentNode] L3 结果为空，降级使用 L2 数据")
                try:
                    posts = self._fetch_l2_results(api_base, session_id, limit)
                    if posts:
                        fallback_used = True
                        logger.info(f"[FilterAgentNode] L2 降级成功，共 {len(posts)} 条")
                    else:
                        logger.warning("[FilterAgentNode] L2 也为空，返回空结果")
                except Exception as e:
                    logger.warning(f"[FilterAgentNode] 获取 L2 降级数据失败: {e}")

            logger.info(f"[FilterAgentNode] 最终结果={len(posts)} 条，降级={fallback_used}")

            return {
                "status":         "success",
                "filtered_data":  posts,          # SentimentAgent 等下游节点兼容字段
                "collected_data": posts,          # XHSFilterNode 输出格式兼容
                "original_count": stats.get("l1_total_posts", 0),
                "filtered_count": len(posts),
                "session_id":     session_id,
                "filter_stats":   stats,
                "fallback_used":  fallback_used,
                "query":          query,
                "message": (
                    f"过滤完成（L2降级）: {stats.get('l1_total_posts',0)} → "
                    f"{stats.get('l2_passed_posts',0)} → {len(posts)} 条"
                    if fallback_used else
                    f"过滤完成: {stats.get('l1_total_posts',0)} → "
                    f"{stats.get('l2_passed_posts',0)} → {len(posts)} 条"
                ),
            }

        except Exception as e:
            logger.error(f"信息过滤失败: {e}", exc_info=True)
            return self._error_result(str(e))

    # ──────────────────────────────────────────────────────────────
    # 内部方法（与 XHSFilterNode 相同的 API 调用逻辑）
    # ──────────────────────────────────────────────────────────────

    def _start_filter(self, api_base: str, query: str,
                      platform: Optional[str], max_posts: int,
                      layer2_mode: str = "normal") -> str:
        payload = {"query": query, "max_posts": max_posts, "auto_save": True,
                   "layer2_mode": layer2_mode}
        if platform:
            payload["platform"] = platform
        resp = requests.post(
            f"{api_base}/api/filter/auto/async",
            json=payload, timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        session_id = data.get("session_id")
        if not session_id:
            raise ValueError(f"过滤引擎未返回 session_id，响应：{data}")
        return session_id

    def _wait_for_completion(self, api_base: str, session_id: str) -> dict:
        url = f"{api_base}/api/frontend/sessions/{session_id}/status"
        deadline = time.time() + POLL_TIMEOUT_S
        while time.time() < deadline:
            try:
                resp = requests.get(url, timeout=15)
                if resp.status_code == 404:
                    time.sleep(POLL_INTERVAL_S)
                    continue
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.warning(f"[FilterAgentNode] 轮询异常，重试: {e}")
                time.sleep(POLL_INTERVAL_S)
                continue

            status   = data.get("status", "processing")
            progress = data.get("progress", 0)
            logger.info(f"[FilterAgentNode] 轮询中 status={status} progress={progress}%")

            if status == "completed":
                return data.get("stats", {})
            if status == "failed":
                raise RuntimeError(f"过滤任务失败: {data.get('error')}")
            time.sleep(POLL_INTERVAL_S)

        raise TimeoutError(f"等待过滤任务超时（{POLL_TIMEOUT_S}s）session_id={session_id}")

    def _fetch_results(self, api_base: str, session_id: str, limit: int) -> List[dict]:
        url = f"{api_base}/api/frontend/sessions/{session_id}/dataset"
        resp = requests.get(url, params={"limit": min(limit, 1000)}, timeout=30)
        resp.raise_for_status()
        return resp.json().get("data") or []

    def _fetch_l2_results(self, api_base: str, session_id: str, limit: int) -> List[dict]:
        url = f"{api_base}/api/frontend/sessions/{session_id}/l2dataset"
        resp = requests.get(url, params={"limit": min(limit, 1000)}, timeout=30)
        resp.raise_for_status()
        return resp.json().get("data") or []

    @staticmethod
    def _error_result(msg: str) -> Dict[str, Any]:
        return {
            "status":         "error",
            "error":          msg,
            "filtered_data":  [],
            "collected_data": [],
            "original_count": 0,
            "filtered_count": 0,
            "session_id":     None,
            "filter_stats":   {},
        }
