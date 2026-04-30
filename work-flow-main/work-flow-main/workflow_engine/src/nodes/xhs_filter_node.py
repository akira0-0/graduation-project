"""
XHS 智能数据过滤节点
============================
对接小红薯数据过滤引擎（三层过滤：DB读取 → 规则过滤 → LLM相关性过滤）。

在工作流中替代 DataCollectionAgentNode + FilterAgentNode 的组合，
输出格式与 SentimentAgentNode 的输入完全兼容。

节点类型名称：XHSFilterAgent
"""
import time
import requests
from typing import Any, Dict, Optional

from ..nodes.base import BaseNode
from ..core.schema import NodeDefinition, WorkflowState
from ..utils.logger import get_logger

logger = get_logger("xhs_filter_node")

# 默认地址，可在节点 params 中覆盖
DEFAULT_FILTER_API_BASE = "http://localhost:8081"

# 轮询参数
POLL_INTERVAL_S = 3      # 每次轮询间隔（秒）
POLL_TIMEOUT_S  = 300    # 最长等待（秒）


class XHSFilterNode(BaseNode):
    """
    XHS 智能数据过滤节点

    工作流 JSON 配置示例：
    {
        "id": "xhs_filter",
        "type": "XHSFilterAgent",
        "config": {
            "title": "XHS数据过滤",
            "params": {
                "query":         "$start_node.topic",   // 引用前序节点输出 或 直接填字符串
                "platform":      "xhs",                 // 可选：xhs / weibo / 不填=全平台
                "max_posts":     500,                   // 最多读取帖子数
                "min_relevance": 0.6,                   // L3最低相关性阈值（0~1）
                "include_comments": true,               // 是否携带评论
                "filter_api_base": "http://localhost:8081"  // 可选，覆盖默认地址
            }
        }
    }

    输出格式（与 SentimentAgent 输入兼容）：
    {
        "status":         "success",
        "collected_data": [
            {
                "id":       "post_id",
                "title":    "帖子标题",
                "content":  "帖子正文",
                "platform": "xhs",
                "url":      "https://...",
                "comments": [...],
                "relevance_score": 0.85,
                ...
            }
        ],
        "total_count":    89,
        "session_id":     "sess_xxx",
        "filter_stats": {
            "l1_total_posts":  500,
            "l2_passed_posts": 234,
            "l3_passed_posts": 89
        },
        "query":          "丽江旅游攻略"
    }
    """

    def __init__(self, node_def: NodeDefinition):
        super().__init__(node_def)

    # ──────────────────────────────────────────────────────────────
    # 主执行逻辑
    # ──────────────────────────────────────────────────────────────

    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        logger.info(f"[XHSFilterNode] 开始执行节点: {self.node_id}")

        # 读取参数
        query           = self.get_input_value(state, "query") or ""
        platform        = self.get_input_value(state, "platform") or None
        max_posts       = self.get_input_value(state, "max_posts") or 500
        min_relevance   = self.get_input_value(state, "min_relevance") or 0.6
        include_comments = self.get_input_value(state, "include_comments")
        if include_comments is None:
            include_comments = True
        api_base        = self.get_input_value(state, "filter_api_base") or DEFAULT_FILTER_API_BASE

        if not query:
            logger.error("[XHSFilterNode] 未获取到 query 参数，请检查节点配置")
            return self._error_result("query 参数为空，请在节点 params 中设置 query 字段")

        logger.info(f"[XHSFilterNode] query={query!r}  platform={platform}  max_posts={max_posts}")

        # ── Step 1: 调用 /api/filter/auto/async 提交任务 ────────
        try:
            session_id, _ = self._start_filter(api_base, query, platform, max_posts,
                                               min_relevance, include_comments)
        except Exception as exc:
            logger.error(f"[XHSFilterNode] 启动过滤失败: {exc}")
            return self._error_result(f"调用过滤引擎失败: {exc}")

        logger.info(f"[XHSFilterNode] 任务已提交，session_id={session_id}")

        # ── Step 2: 轮询 /api/frontend/sessions/{id}/status 等任务完成
        try:
            stats = self._wait_for_completion(api_base, session_id)
        except Exception as exc:
            logger.error(f"[XHSFilterNode] 等待任务失败: {exc}")
            return self._error_result(f"过滤任务未完成: {exc}")

        logger.info(f"[XHSFilterNode] 过滤完成，stats={stats}")

        # ── Step 3: 获取结果 /api/frontend/sessions/{id}/dataset ─
        try:
            posts = self._poll_results(api_base, session_id)
        except Exception as exc:
            logger.error(f"[XHSFilterNode] 获取结果失败: {exc}")
            return self._error_result(f"获取过滤结果失败: {exc}")

        # ── Step 3b: L3=0 时降级使用 L2 数据 ────────────────────
        fallback_used = False
        if len(posts) == 0:
            l2_count = stats.get("l2_passed_posts", 0)
            logger.warning(
                f"[XHSFilterNode] L3 结果为空，尝试降级到 L2 数据（L2 共 {l2_count} 条）"
            )
            try:
                posts = self._poll_l2_results(api_base, session_id)
                if posts:
                    fallback_used = True
                    logger.info(f"[XHSFilterNode] 降级成功，使用 L2 数据 {len(posts)} 条")
                else:
                    logger.warning("[XHSFilterNode] L2 数据也为空，返回空结果")
            except Exception as exc:
                logger.warning(f"[XHSFilterNode] 获取 L2 降级数据失败: {exc}，返回空结果")

        logger.info(f"[XHSFilterNode] 过滤完成，最终帖子数={len(posts)}，降级={fallback_used}")

        # ── Step 4: 格式化输出（与 SentimentAgentNode 兼容）──────
        return {
            "status":         "success",
            "collected_data": posts,       # SentimentAgent 读取此字段
            "total_count":    len(posts),
            "session_id":     session_id,
            "filter_stats":   stats,
            "fallback_used":  fallback_used,
            "fallback_layer": "l2" if fallback_used else None,
            "query":          query,
            "message":        (
                f"XHS过滤完成（L2降级）：{stats.get('l1_total_posts',0)} → "
                f"{stats.get('l2_passed_posts',0)} → {len(posts)} 条"
                if fallback_used else
                f"XHS过滤完成：{stats.get('l1_total_posts',0)} → "
                f"{stats.get('l2_passed_posts',0)} → {len(posts)} 条"
            )
        }

    # ──────────────────────────────────────────────────────────────
    # 内部方法
    # ──────────────────────────────────────────────────────────────

    def _start_filter(self, api_base: str, query: str, platform: Optional[str],
                      max_posts: int, min_relevance: float,
                      include_comments: bool):
        """
        调用 POST /api/filter/auto/async（异步接口，立即返回 session_id）。
        返回 (session_id, stats_dict_初始值)
        """
        payload = {
            "query":     query,
            "max_posts": max_posts,
            "auto_save": True,
        }
        if platform:
            payload["platform"] = platform

        resp = requests.post(
            f"{api_base}/api/filter/auto/async",
            json=payload,
            timeout=15,   # 只是提交任务，15s 内必须收到响应
        )
        resp.raise_for_status()
        data = resp.json()

        session_id = data.get("session_id")
        if not session_id:
            raise ValueError(f"过滤引擎未返回 session_id，响应：{data}")

        return session_id, {}   # stats 在任务完成后再从 status 接口读

    def _wait_for_completion(self, api_base: str, session_id: str) -> dict:
        """
        轮询 GET /api/frontend/sessions/{session_id}/status
        直到 status == "completed"，返回最终 stats。
        """
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
                logger.warning(f"[XHSFilterNode] 轮询状态异常，重试: {e}")
                time.sleep(POLL_INTERVAL_S)
                continue

            status   = data.get("status", "processing")
            progress = data.get("progress", 0)
            stats    = data.get("stats", {})
            logger.info(f"[XHSFilterNode] 轮询中 status={status} progress={progress}%")

            if status == "completed":
                return stats
            if status == "failed":
                raise RuntimeError(f"过滤任务失败: {data.get('error')}")

            time.sleep(POLL_INTERVAL_S)

        raise TimeoutError(f"等待过滤任务超时（{POLL_TIMEOUT_S}s），session_id={session_id}")

    def _poll_results(self, api_base: str, session_id: str) -> list:
        """
        任务完成后，调用 GET /api/frontend/sessions/{session_id}/dataset
        获取 L3 CommentData 格式的帖子列表。
        """
        url = f"{api_base}/api/frontend/sessions/{session_id}/dataset"
        resp = requests.get(url, params={"limit": 1000}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data") or []

    def _poll_l2_results(self, api_base: str, session_id: str) -> list:
        """
        降级接口：调用 GET /api/frontend/sessions/{session_id}/l2dataset
        获取 Layer-2 规则过滤后的帖子列表（当 L3=0 时使用）。
        """
        url = f"{api_base}/api/frontend/sessions/{session_id}/l2dataset"
        resp = requests.get(url, params={"limit": 1000}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data") or []

    @staticmethod
    def _error_result(msg: str) -> Dict[str, Any]:
        return {
            "status":         "error",
            "error":          msg,
            "collected_data": [],
            "total_count":    0,
            "session_id":     None,
            "filter_stats":   {},
        }
