"""Tree → boxes and selector matching (shared by every tree backend)."""

from typing import Any

from mphone_core.tree import nodes_to_boxes, select


def node(
    nid: str,
    parent: str | None,
    text: str = "",
    rect: tuple[int, int, int, int] = (0, 0, 100, 50),
    **extra: Any,
) -> dict[str, Any]:
    left, top, right, bottom = rect
    return {
        "node_id": nid,
        "parent_id": parent,
        "text": text,
        "rect": {"left": left, "top": top, "right": right, "bottom": bottom},
        **extra,
    }


NODES = [
    node("root", None, rect=(0, 0, 1080, 2400)),
    node("list", "root", rect=(0, 300, 1080, 2000), resource_id="com.x:id/list"),
    node("row1", "list", rect=(0, 300, 1080, 450), clickable=True),
    node("row1t", "row1", "İletişim", rect=(40, 330, 500, 420)),
    node(
        "send",
        "root",
        rect=(950, 2200, 1060, 2300),
        content_desc="Gönder",
        clickable=True,
        resource_id="com.x:id/send",
    ),
    node("field", "root", rect=(40, 2200, 900, 2300), editable=True),
    node("hidden", "root", "gizli", visible=False),
    node("zero", "root", "sıfır", rect=(10, 10, 10, 10)),
    node("pwd", "root", rect=(40, 1000, 900, 1100), editable=True, password=True),
]


def test_boxes_keep_labelled_visible_and_editable() -> None:
    boxes = nodes_to_boxes(NODES)
    labels = [(b["text"], b["node_id"]) for b in boxes]
    assert ("İletişim", "row1t") in labels
    assert ("Gönder", "send") in labels  # labelled by content_desc
    assert ("", "field") in labels  # empty field kept: agents must find it to tap
    assert all(b["node_id"] not in ("hidden", "zero", "root", "list") for b in boxes)
    pwd = next(b for b in boxes if b["node_id"] == "pwd")
    assert pwd["password"] is True and pwd["editable"] is True


def test_clickable_ancestor() -> None:
    label = next(b for b in nodes_to_boxes(NODES) if b["node_id"] == "row1t")
    assert label["clickable"] is False
    assert label["clickable_ancestor"] == {"x": 540, "y": 375}


def test_selectors() -> None:
    assert [b["node_id"] for b in select(NODES, {"query": "gonder"})] == ["send"]
    assert [b["node_id"] for b in select(NODES, {"resource_id": "send"})] == ["send"]
    assert [b["node_id"] for b in select(NODES, {"text": "iletişim"})] == ["row1t"]
    assert [b["node_id"] for b in select(NODES, {"text_regex": "^İle"})] == ["row1t"]
    assert [b["node_id"] for b in select(NODES, {"clickable": True, "within": {"resource_id": "list"}})] == [
        "row1"
    ]
    assert select(NODES, {"text": "gizli"}) == []
    assert len(select(NODES, {"clickable": True})) == 2
    assert [b["node_id"] for b in select(NODES, {"clickable": True, "index": 1})] == ["send"]
