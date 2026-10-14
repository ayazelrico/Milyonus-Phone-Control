"""Accessibility-tree utilities shared by every backend that has a tree (A1.07, A2.05, A7.03).

Backends parse their platform's tree into protocol `Node` dicts; everything after that —
turning nodes into tap-ready boxes and matching selectors — lives here once, so Android,
Companion and WDA cannot drift apart on what "clickable ancestor" or "text_contains" means.
"""

import re
from collections.abc import Iterable
from typing import Any

from .textnorm import match

NodeDict = dict[str, Any]
BoxDict = dict[str, Any]


def _centre(rect: dict[str, int]) -> tuple[int, int, int, int]:
    w = max(0, rect["right"] - rect["left"])
    h = max(0, rect["bottom"] - rect["top"])
    return rect["left"] + w // 2, rect["top"] + h // 2, w, h


def _label(node: NodeDict) -> str:
    return (node.get("text") or "").strip() or (node.get("content_desc") or "").strip()


def node_to_box(node: NodeDict, by_id: dict[str, NodeDict] | None = None) -> BoxDict:
    x, y, w, h = _centre(node["rect"])
    ancestor = None
    if by_id is not None and not node.get("clickable"):
        parent_id = node.get("parent_id")
        while parent_id and parent_id in by_id:
            parent = by_id[parent_id]
            if parent.get("clickable"):
                px, py, _, _ = _centre(parent["rect"])
                ancestor = {"x": px, "y": py}
                break
            parent_id = parent.get("parent_id")
    return {
        "text": _label(node),
        "confidence": 1.0,
        "source": "tree",
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "node_id": node.get("node_id"),
        "resource_id": node.get("resource_id"),
        "content_desc": node.get("content_desc"),
        "class": node.get("class"),
        "clickable": bool(node.get("clickable")),
        "clickable_ancestor": ancestor,
        "focused": bool(node.get("focused")),
        "editable": bool(node.get("editable")),
        "password": bool(node.get("password")),
    }


def nodes_to_boxes(nodes: list[NodeDict]) -> list[BoxDict]:
    """The visible, labelled, non-empty nodes as boxes, top-to-bottom then left-to-right.

    Editable fields are kept even when empty: an agent must be able to find the field to tap.
    """
    by_id = {n["node_id"]: n for n in nodes}
    boxes: list[BoxDict] = []
    for node in nodes:
        if not node.get("visible", True):
            continue
        _, _, w, h = _centre(node["rect"])
        if w == 0 or h == 0:
            continue
        if not _label(node) and not node.get("editable"):
            continue
        boxes.append(node_to_box(node, by_id))
    boxes.sort(key=lambda b: (b["y"], b["x"]))
    return boxes


def _text_ok(selector: dict[str, Any], node: NodeDict) -> bool:
    text = node.get("text") or ""
    if (want := selector.get("text")) is not None and match(want, text, exact=True) is None:
        return False
    if (want := selector.get("text_contains")) is not None and match(want, text) is None:
        return False
    if (pattern := selector.get("text_regex")) is not None and not re.search(pattern, text):
        return False
    if (want := selector.get("content_desc")) is not None and match(
        want, node.get("content_desc") or ""
    ) is None:
        return False
    if (query := selector.get("query")) is not None:
        fields = [text, node.get("content_desc") or "", node.get("resource_id") or ""]
        if all(match(query, f) is None for f in fields):
            return False
    return True


def _node_matches(selector: dict[str, Any], node: NodeDict) -> bool:
    if not node.get("visible", True) or not _text_ok(selector, node):
        return False
    rid = selector.get("resource_id")
    if (
        rid is not None
        and node.get("resource_id") != rid
        and not (node.get("resource_id") or "").endswith(":id/" + rid)
    ):
        return False
    if (cls := selector.get("class")) is not None and node.get("class") != cls:
        return False
    for flag in ("clickable", "enabled"):
        if (want := selector.get(flag)) is not None and bool(node.get(flag, flag == "enabled")) != want:
            return False
    return True


def _descendants(nodes: list[NodeDict], roots: Iterable[str]) -> set[str]:
    children: dict[str, list[str]] = {}
    for n in nodes:
        if n.get("parent_id"):
            children.setdefault(n["parent_id"], []).append(n["node_id"])
    out: set[str] = set()
    stack = list(roots)
    while stack:
        current = stack.pop()
        for child in children.get(current, []):
            if child not in out:
                out.add(child)
                stack.append(child)
    return out


def select(nodes: list[NodeDict], selector: dict[str, Any]) -> list[BoxDict]:
    """Nodes matching `selector` as boxes. `index` picks one match; `within` scopes the search."""
    pool = nodes
    if (within := selector.get("within")) is not None:
        roots = [n["node_id"] for n in nodes if _node_matches(within, n)]
        allowed = _descendants(nodes, roots)
        pool = [n for n in nodes if n["node_id"] in allowed]
    by_id = {n["node_id"]: n for n in nodes}
    hits = [node_to_box(n, by_id) for n in pool if _node_matches(selector, n)]
    hits.sort(key=lambda b: (b["y"], b["x"]))
    index = selector.get("index")
    if index is not None:
        return hits[index : index + 1]
    return hits
