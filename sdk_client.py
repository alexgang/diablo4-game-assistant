import json
import logging
import mimetypes
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class GamingAssistantSDK:
    """Python client for the Intel Gaming Assistant SDK HTTP API."""

    def __init__(self, base_url: str = "http://127.0.0.1:9190"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.trust_env = False
        os.environ.pop("HTTPS_PROXY", None)
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("https_proxy", None)
        os.environ.pop("http_proxy", None)

    def _post_json(self, path: str, body: dict) -> Any:
        resp = self.session.post(f"{self.base_url}{path}", json=body)
        resp.raise_for_status()
        return resp.json()

    def _post_multipart_json(self, path: str, data: dict, files: list) -> Any:
        resp = self.session.post(f"{self.base_url}{path}", data=data, files=files)
        resp.raise_for_status()
        return resp.json()

    def _stream_sse(self, path: str, body: dict) -> List[dict]:
        resp = self.session.post(
            f"{self.base_url}{path}", json=body, stream=True
        )
        resp.raise_for_status()
        chunks = []
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data: "):
                payload = line[len("data: "):]
                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                chunks.append(chunk)
                if chunk.get("fin") is True:
                    break
        return chunks

    def _check(self, resp: dict) -> Any:
        if resp.get("code") != "ok":
            raise RuntimeError(
                f"SDK error: code={resp.get('code')}, msg={resp.get('msg', resp.get('message', ''))}"
            )
        return resp.get("data", resp)

    def check_server(self) -> bool:
        try:
            resp = self.session.get(self.base_url, timeout=5)
            resp.raise_for_status()
            return True
        except requests.ConnectionError:
            logger.warning(f"SDK服务器连接失败: {self.base_url}")
            return False
        except Exception as e:
            logger.warning(f"SDK服务器检查失败: {e}")
            return False

    def init_all(self, instance_id: str) -> int:
        """初始化所有 SDK 服务。

        Returns:
            int: 成功初始化的服务数量
        """
        services = [
            ("vision", self.vision_init),
            ("knowledge", self.knowledge_init),
            ("memory", self.memory_init),
            ("mmr", self.mmr_init),
            ("bar", self.bar_init),
        ]
        ok_count = 0
        for name, init_fn in services:
            try:
                init_fn(instance_id)
                ok_count += 1
            except Exception as e:
                msg = str(e)
                if "has existed" in msg or "already exist" in msg:
                    # instance 已存在（上次进程未释放），先 destroy 再重试
                    logger.info(f"SDK {name} instance 已存在,尝试 destroy 后重新 init")
                    self._destroy_service(name, instance_id)
                    try:
                        init_fn(instance_id)
                        logger.info(f"SDK {name} 重新初始化成功")
                        ok_count += 1
                    except Exception as e2:
                        logger.warning(f"SDK {name} 重新初始化仍失败: {e2}")
                else:
                    logger.warning(f"SDK {name} 初始化失败: {e}")
        return ok_count

    def _destroy_service(self, service: str, instance_id: str) -> bool:
        """销毁 SDK 服务 instance（用于 instance 冲突时清理）

        Args:
            service: 服务名 (vision/knowledge/memory/mmr/bar)
            instance_id: instance ID

        Returns:
            bool: 是否销毁成功
        """
        try:
            resp = self._post_json(f"/{service}/service/destroy/{instance_id}", {})
            self._check(resp)
            logger.info(f"SDK {service} instance 已销毁: {instance_id}")
            return True
        except Exception as e:
            logger.debug(f"SDK {service} destroy 失败(可能不支持): {e}")
            return False

    # ── Vision ──────────────────────────────────────────────────────────

    def vision_init(self, instance_id: str) -> Any:
        """Initialize a Vision service instance."""
        resp = self._post_json(f"/vision/service/init/{instance_id}", {})
        return self._check(resp)

    def vision_insert_scene(
        self,
        instance_id: str,
        scene_id: str,
        image_paths: List[str],
        pictures_id: str,
        mode: str = "accurate",
    ) -> Any:
        """Insert scene images into a Vision instance."""
        files = []
        try:
            for p in image_paths:
                mime = mimetypes.guess_type(p)[0] or "application/octet-stream"
                files.append(("pictures", (os.path.basename(p), open(p, "rb"), mime)))
            data = {"pictures_id": pictures_id, "mode": mode}
            resp = self._post_multipart_json(
                f"/vision/scene/insert/{instance_id}/{scene_id}", data, files
            )
            return self._check(resp)
        finally:
            for _, f_tuple in files:
                f_tuple[1].close()

    def vision_build(
        self,
        instance_id: str,
        mode: str = "accurate",
        full_build: bool = False,
    ) -> Dict[str, Any]:
        """Build the Vision index; returns {threshold, threshold_2}."""
        body = {"mode": mode, "full_build": full_build, "auto_threshold": True}
        chunks = self._stream_sse(f"/vision/service/build/{instance_id}", body)
        for chunk in reversed(chunks):
            if "threshold" in chunk:
                return {
                    "threshold": chunk.get("threshold"),
                    "threshold_2": chunk.get("threshold_2"),
                }
        last = chunks[-1] if chunks else {}
        return {
            "threshold": last.get("threshold"),
            "threshold_2": last.get("threshold_2"),
        }

    def vision_query(
        self,
        instance_id: str,
        image_path: str,
        threshold: int = -1,
        threshold_2: int = -1,
        topk: int = 1,
        mode: str = "accurate",
    ) -> List[Dict[str, Any]]:
        """Query the Vision index; returns list of {scene_id, picture_id, score}."""
        mime = mimetypes.guess_type(image_path)[0] or "application/octet-stream"
        files = [("file", (os.path.basename(image_path), open(image_path, "rb"), mime))]
        try:
            data = {
                "topk": str(topk),
                "threshold": str(threshold),
                "threshold_2": str(threshold_2),
                "mode": mode,
            }
            resp = self._post_multipart_json(
                f"/vision/service/query/{instance_id}", data, files
            )
            result = self._check(resp)
            return result if isinstance(result, list) else [result]
        finally:
            for _, f_tuple in files:
                f_tuple[1].close()

    # ── Knowledge / RAG ─────────────────────────────────────────────────

    def knowledge_init(self, instance_id: str) -> Any:
        """Initialize a Knowledge service instance."""
        resp = self._post_json(f"/knowledge/service/init/{instance_id}", {})
        return self._check(resp)

    def knowledge_insert(
        self,
        instance_id: str,
        knowledge_id: str,
        text_paths: List[str],
        texts_id: str,
    ) -> Any:
        """Insert text files into a Knowledge instance."""
        files = []
        try:
            for p in text_paths:
                mime = mimetypes.guess_type(p)[0] or "application/octet-stream"
                files.append(("texts", (os.path.basename(p), open(p, "rb"), mime)))
            data = {"texts_id": texts_id}
            resp = self._post_multipart_json(
                f"/knowledge/knowledge/insert/{instance_id}/{knowledge_id}", data, files
            )
            return self._check(resp)
        finally:
            for _, f_tuple in files:
                f_tuple[1].close()

    def knowledge_build(self, instance_id: str, full_build: bool = False) -> Any:
        """Build the Knowledge index."""
        chunks = self._stream_sse(
            f"/knowledge/service/build/{instance_id}", {"full_build": full_build}
        )
        return self._check(chunks[-1]) if chunks else None

    def knowledge_query(
        self,
        instance_id: str,
        text: str,
        knowledge_id: Optional[str] = None,
        scenes_name: Optional[str] = None,
    ) -> str:
        """Query the Knowledge index; returns concatenated answer string."""
        body: Dict[str, Any] = {"text": text}
        if knowledge_id is not None:
            body["knowledge_id"] = [knowledge_id] if isinstance(knowledge_id, str) else knowledge_id
        if scenes_name is not None:
            body["scenes_name"] = [scenes_name] if isinstance(scenes_name, str) else scenes_name
        chunks = self._stream_sse(f"/knowledge/service/query/{instance_id}", body)
        parts = []
        for chunk in chunks:
            msg = chunk.get("message", "")
            if msg:
                parts.append(msg)
        return "".join(parts)

    # ── Memory ──────────────────────────────────────────────────────────

    def memory_init(self, instance_id: str) -> Any:
        """Initialize a Memory service instance."""
        resp = self._post_json("/memory/service/init", {"instance_id": instance_id})
        return self._check(resp)

    def memory_insert(
        self,
        instance_id: str,
        record_id: str,
        info: str,
        tags: Optional[List[str]] = None,
        emb_props: Optional[Dict[str, Any]] = None,
        image_paths: Optional[List[str]] = None,
    ) -> Any:
        """Insert a record into Memory."""
        payload: Dict[str, Any] = {
            "instance_id": instance_id,
            "record_id": record_id,
            "info": info,
        }
        if tags is not None:
            payload["tags"] = tags
        if emb_props is not None:
            payload["emb_props"] = emb_props
        data = {"data": json.dumps(payload)}
        files = []
        try:
            if image_paths:
                for p in image_paths:
                    mime = mimetypes.guess_type(p)[0] or "application/octet-stream"
                    files.append(("images", (os.path.basename(p), open(p, "rb"), mime)))
            resp = self._post_multipart_json("/memory/record/insert", data, files)
            return self._check(resp)
        finally:
            for _, f_tuple in files:
                f_tuple[1].close()

    def memory_search(
        self,
        instance_id: str,
        text: str,
        topk: int = 5,
        threshold: float = 0.1,
    ) -> Any:
        """Search Memory by text."""
        resp = self._post_json(
            "/memory/service/search/text",
            {"instance_id": instance_id, "text": text, "topk": topk, "threshold": threshold},
        )
        return self._check(resp)

    def memory_list(
        self, instance_id: str, indices: Optional[List[str]] = None
    ) -> Any:
        """List Memory records."""
        body: Dict[str, Any] = {"instance_id": instance_id}
        if indices is not None:
            body["indices"] = indices
        resp = self._post_json("/memory/record/list", body)
        return self._check(resp)

    def memory_delete(self, instance_id: str, record_id: str) -> Any:
        """Delete a Memory record."""
        resp = self._post_json(
            "/memory/record/delete", {"instance_id": instance_id, "record_id": record_id}
        )
        return self._check(resp)

    # ── MMR ─────────────────────────────────────────────────────────────

    def mmr_init(self, instance_id: str) -> Any:
        """Initialize an MMR service instance."""
        resp = self._post_json("/mmr/service/init", {"instance_id": instance_id})
        return self._check(resp)

    def mmr_insert(
        self,
        instance_id: str,
        text: str,
        info: Optional[str] = None,
        image_path: Optional[str] = None,
    ) -> Any:
        """Insert a record into MMR."""
        payload: Dict[str, Any] = {"instance_id": instance_id, "text": text}
        if info is not None:
            payload["info"] = info
        data = {"data": json.dumps(payload)}
        files = []
        try:
            if image_path:
                mime = mimetypes.guess_type(image_path)[0] or "application/octet-stream"
                files.append(
                    ("filedata", (os.path.basename(image_path), open(image_path, "rb"), mime))
                )
            resp = self._post_multipart_json("/mmr/record/insert", data, files)
            return self._check(resp)
        finally:
            for _, f_tuple in files:
                f_tuple[1].close()

    def mmr_build(self, instance_id: str) -> Any:
        """Build the MMR index."""
        resp = self._post_json("/mmr/service/build", {"instance_id": instance_id})
        return self._check(resp)

    def mmr_query(
        self,
        instance_id: str,
        text: Optional[str] = None,
        image_path: Optional[str] = None,
        topk: int = 1,
        threshold: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Query MMR; returns list of {score, text, info}."""
        payload: Dict[str, Any] = {
            "instance_id": instance_id,
            "topk": topk,
            "threshold": threshold,
        }
        if text is not None:
            payload["text"] = text
        data = {"data": json.dumps(payload)}
        files = []
        try:
            if image_path:
                mime = mimetypes.guess_type(image_path)[0] or "application/octet-stream"
                files.append(
                    ("filedata", (os.path.basename(image_path), open(image_path, "rb"), mime))
                )
            resp = self._post_multipart_json("/mmr/service/query", data, files)
            result = self._check(resp)
            raw = result.get("raw", result) if isinstance(result, dict) else result
            if isinstance(raw, list) and len(raw) > 0:
                items = raw[0] if isinstance(raw[0], list) else raw
                return [
                    {"score": item.get("score"), "text": item.get("text"), "info": item.get("info")}
                    for item in items
                ]
            return []
        finally:
            for _, f_tuple in files:
                f_tuple[1].close()

    # ── ASR ─────────────────────────────────────────────────────────────

    def asr_transcribe(self, audio_path: str, hotwords: str = "") -> str:
        """Transcribe an audio file; returns the transcribed text."""
        mime = mimetypes.guess_type(audio_path)[0] or "application/octet-stream"
        files = [("file", (os.path.basename(audio_path), open(audio_path, "rb"), mime))]
        try:
            data = {"hotwords": hotwords}
            resp = self._post_multipart_json("/asr/service/query/file", data, files)
            result = self._check(resp)
            if isinstance(result, dict):
                return result.get("text", result.get("result", str(result)))
            return str(result)
        finally:
            for _, f_tuple in files:
                f_tuple[1].close()

    # ── BAR ─────────────────────────────────────────────────────────────

    def bar_init(self, instance_id: str) -> Any:
        """Initialize a BAR service instance."""
        resp = self._post_json("/bar/service/init", {"instance_id": instance_id})
        return self._check(resp)

    def bar_annotate_boss(
        self,
        instance_id: str,
        boss_id: str,
        action_id: str,
        frame_paths: List[str],
        annotations: List[Dict[str, Any]],
        is_background_action: bool = False,
    ) -> Any:
        """Atomic: reset → insert frames → annotate each → process → build."""
        self._post_json("/bar/service/reset", {"instance_id": instance_id, "keep_db": False})

        for fp in frame_paths:
            mime = mimetypes.guess_type(fp)[0] or "application/octet-stream"
            files = [("frame", (os.path.basename(fp), open(fp, "rb"), mime))]
            try:
                data = {"instance_id": instance_id, "boss_id": boss_id, "action_id": action_id}
                resp = self._post_multipart_json("/bar/frame/insert", data, files)
                self._check(resp)
            finally:
                for _, f_tuple in files:
                    f_tuple[1].close()

        for ann in annotations:
            body = {"instance_id": instance_id, "boss_id": boss_id, "action_id": action_id}
            body.update(ann)
            resp = self._post_json("/bar/frame/annotate", body)
            self._check(resp)

        resp = self._post_json(
            "/bar/service/process",
            {"instance_id": instance_id, "is_background_action": is_background_action},
        )
        self._check(resp)

        resp = self._post_json("/bar/service/build", {"instance_id": instance_id})
        return self._check(resp)

    def bar_query(
        self,
        instance_id: str,
        boss_id: str,
        frame_path: str,
        k_actions: int = 3,
    ) -> Dict[str, Any]:
        """Atomic: reset(wipe) → boss/query. Returns {results, masks}."""
        self._post_json("/bar/service/reset", {"instance_id": instance_id, "wipe_db": True})

        mime = mimetypes.guess_type(frame_path)[0] or "application/octet-stream"
        files = [("frame", (os.path.basename(frame_path), open(frame_path, "rb"), mime))]
        try:
            data = {"instance_id": instance_id, "boss_id": boss_id, "k_actions": k_actions}
            resp = self._post_multipart_json("/bar/boss/query", data, files)
            result = self._check(resp)
            if isinstance(result, dict):
                return {"results": result.get("results", []), "masks": result.get("masks", [])}
            return {"results": [], "masks": []}
        finally:
            for _, f_tuple in files:
                f_tuple[1].close()

    def bar_track_live(self, instance_id: str, frame_path: str) -> Any:
        """Live tracking via BAR."""
        mime = mimetypes.guess_type(frame_path)[0] or "application/octet-stream"
        files = [("frame", (os.path.basename(frame_path), open(frame_path, "rb"), mime))]
        try:
            data = {"instance_id": instance_id}
            resp = self._post_multipart_json("/bar/frame/live/track", data, files)
            return self._check(resp)
        finally:
            for _, f_tuple in files:
                f_tuple[1].close()
