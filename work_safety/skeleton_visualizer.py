"""
skeleton_visualizer.py
Draws MediaPipe-style ergonomic skeletons and risk overlays on video frames.
Colors bones and joints dynamically according to real-time RULA risk level (Safe=Teal, Warning=Amber, Critical=Red).
Implements precise text-width collision detection (via cv2.getTextSize) to prevent overlapping labels
when workers are positioned in close spatial proximity by vertically and horizontally staggering label boxes.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any


@dataclass
class Joint2D:
    """2D pixel coordinate with confidence."""
    x: float
    y: float
    confidence: float = 1.0


@dataclass
class LabelBox:
    """Bounding box for rendered text label."""
    worker_id: str
    x_min: int
    y_min: int
    x_max: int
    y_max: int
    anchor_x: int
    anchor_y: int
    lines: List[str]
    color_bgr: Tuple[int, int, int]
    bg_bgr: Tuple[int, int, int]

    def overlaps(self, other: "LabelBox", padding: int = 4) -> bool:
        """Check if this bounding box intersects another bounding box with safety padding."""
        return not (
            (self.x_max + padding) < (other.x_min - padding)
            or (self.x_min - padding) > (other.x_max + padding)
            or (self.y_max + padding) < (other.y_min - padding)
            or (self.y_min - padding) > (other.y_max + padding)
        )


@dataclass
class WorkerSkeletonVisual:
    """Data required to render one worker's skeleton and ergonomic overlay."""
    worker_id: str
    risk_level: str               # "safe" | "warning" | "critical"
    rula_score: int
    sustained_seconds: float
    joints: Dict[str, Joint2D]    # e.g. "nose", "neck", "left_shoulder", "right_shoulder", ...
    has_active_alert: bool = False


class SkeletonVisualizer:
    """
    OpenCV and standalone skeleton renderer for factory floor ergonomic perception.
    """

    # BGR Color Palettes for High-Contrast Visibility
    COLOR_SAFE = (180, 210, 0)       # Teal / Cyan-Green (BGR)
    COLOR_WARNING = (0, 165, 255)    # Amber / Orange (BGR)
    COLOR_CRITICAL = (30, 30, 230)   # High-Alert Red (BGR)

    BG_SAFE = (20, 40, 20)
    BG_WARNING = (10, 30, 50)
    BG_CRITICAL = (15, 15, 60)

    # MediaPipe / COCO Standard Human Topology Bones
    SKELETON_CONNECTIONS: List[Tuple[str, str]] = [
        # Upper body & Arms
        ("neck", "nose"),
        ("neck", "left_shoulder"),
        ("neck", "right_shoulder"),
        ("left_shoulder", "left_elbow"),
        ("left_elbow", "left_wrist"),
        ("right_shoulder", "right_elbow"),
        ("right_elbow", "right_wrist"),
        # Spine & Trunk
        ("left_shoulder", "right_shoulder"),
        ("neck", "spine"),
        ("spine", "mid_hip"),
        ("mid_hip", "left_hip"),
        ("mid_hip", "right_hip"),
        ("left_hip", "right_hip"),
        # Lower body & Legs
        ("left_hip", "left_knee"),
        ("left_knee", "left_ankle"),
        ("right_hip", "right_knee"),
        ("right_knee", "right_ankle"),
    ]

    def __init__(self, font_scale: float = 0.5, font_thickness: int = 1):
        self.font_scale = font_scale
        self.font_thickness = font_thickness

    def get_risk_colors(self, risk_level: str) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        """Get (primary_color_bgr, background_color_bgr) for a risk level."""
        lvl = (risk_level or "safe").lower()
        if lvl == "critical":
            return self.COLOR_CRITICAL, self.BG_CRITICAL
        elif lvl == "warning":
            return self.COLOR_WARNING, self.BG_WARNING
        else:
            return self.COLOR_SAFE, self.BG_SAFE

    def compute_label_box(
        self,
        worker: WorkerSkeletonVisual,
        placed_boxes: List[LabelBox],
        frame_width: int = 1280,
        frame_height: int = 720,
        get_text_size_fn: Optional[Any] = None,
    ) -> LabelBox:
        """
        Compute non-overlapping label bounding box using actual rendered text dimensions.
        Employs collision-free candidate slot searching (vertical staggering tiers and horizontal shifts).
        """
        color_bgr, bg_bgr = self.get_risk_colors(worker.risk_level)

        status_tag = f"RULA {worker.rula_score} [{worker.risk_level.upper()}]"
        if worker.has_active_alert:
            status_tag += " [ALERT!]"
        elif worker.sustained_seconds > 5.0:
            status_tag += f" ({worker.sustained_seconds:.0f}s)"

        lines = [
            f"Worker: {worker.worker_id}",
            status_tag,
        ]

        if "nose" in worker.joints:
            anchor_x = int(worker.joints["nose"].x)
            anchor_y = int(worker.joints["nose"].y)
        elif "neck" in worker.joints:
            anchor_x = int(worker.joints["neck"].x)
            anchor_y = int(worker.joints["neck"].y)
        else:
            xs = [j.x for j in worker.joints.values()]
            ys = [j.y for j in worker.joints.values()]
            anchor_x = int(sum(xs) / len(xs)) if xs else 100
            anchor_y = int(min(ys)) if ys else 100

        max_line_width = 0
        total_text_height = 0
        for line in lines:
            if get_text_size_fn is not None:
                (w, h), _ = get_text_size_fn(line)
            else:
                w = int(len(line) * 8.5)
                h = 14
            max_line_width = max(max_line_width, w)
            total_text_height += h + 6

        padding_x = 8
        padding_y = 6
        box_width = max_line_width + 2 * padding_x
        box_height = total_text_height + 2 * padding_y

        # Generate prioritized list of candidate offsets (dy, dx)
        # Tier 1: Staggering above anchor (y - box_height - 15, y - 2*box_height - 25, etc.)
        # Tier 2: Staggering below anchor
        # Tier 3: Lateral shifts (left/right)
        candidate_slots: List[Tuple[int, int]] = []

        # Levels above anchor (0, 1, 2, 3, 4, 5)
        for level in range(6):
            dy = -(box_height + 15 + level * (box_height + 10))
            candidate_slots.append((dy, 0))
            candidate_slots.append((dy, -(box_width // 2)))
            candidate_slots.append((dy, (box_width // 2)))

        # Levels below anchor
        for level in range(4):
            dy = 50 + level * (box_height + 10)
            candidate_slots.append((dy, 0))
            candidate_slots.append((dy, -(box_width // 2)))
            candidate_slots.append((dy, (box_width // 2)))

        best_candidate: Optional[LabelBox] = None

        for dy, dx in candidate_slots:
            cand_x_min = int(anchor_x - box_width // 2 + dx)
            cand_y_min = int(anchor_y + dy)

            # Frame boundary clamping
            cand_x_min = max(5, min(frame_width - box_width - 5, cand_x_min))
            cand_y_min = max(5, min(frame_height - box_height - 5, cand_y_min))

            cand = LabelBox(
                worker_id=worker.worker_id,
                x_min=cand_x_min,
                y_min=cand_y_min,
                x_max=cand_x_min + box_width,
                y_max=cand_y_min + box_height,
                anchor_x=anchor_x,
                anchor_y=anchor_y,
                lines=lines,
                color_bgr=color_bgr,
                bg_bgr=bg_bgr,
            )

            # Check if this candidate collides with any previously placed box
            if not any(cand.overlaps(pb, padding=3) for pb in placed_boxes):
                best_candidate = cand
                break

        if best_candidate is None:
            # Fallback if extremely crowded: default clamped
            cand_x_min = max(5, min(frame_width - box_width - 5, int(anchor_x - box_width // 2)))
            cand_y_min = max(5, min(frame_height - box_height - 5, int(anchor_y - box_height - 15)))
            best_candidate = LabelBox(
                worker_id=worker.worker_id,
                x_min=cand_x_min,
                y_min=cand_y_min,
                x_max=cand_x_min + box_width,
                y_max=cand_y_min + box_height,
                anchor_x=anchor_x,
                anchor_y=anchor_y,
                lines=lines,
                color_bgr=color_bgr,
                bg_bgr=bg_bgr,
            )

        return best_candidate

    def draw_skeleton_on_frame(
        self,
        frame: Any,  # numpy ndarray
        workers: List[WorkerSkeletonVisual],
    ) -> Tuple[Any, List[LabelBox]]:
        """Render multi-worker skeletons and collision-free ergonomic labels using OpenCV."""
        try:
            import cv2
            has_cv2 = True
        except ImportError:
            has_cv2 = False

        placed_label_boxes: List[LabelBox] = []
        if not has_cv2:
            return frame, placed_label_boxes

        height, width = frame.shape[:2]

        def get_text_size(text: str):
            (tw, th), bl = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, self.font_scale, self.font_thickness)
            return (tw, th), bl

        for worker in workers:
            lbox = self.compute_label_box(
                worker=worker,
                placed_boxes=placed_label_boxes,
                frame_width=width,
                frame_height=height,
                get_text_size_fn=get_text_size,
            )
            placed_label_boxes.append(lbox)

        for worker in workers:
            color_bgr, bg_bgr = self.get_risk_colors(worker.risk_level)
            joints = worker.joints

            for j1_name, j2_name in self.SKELETON_CONNECTIONS:
                if j1_name in joints and j2_name in joints:
                    j1 = joints[j1_name]
                    j2 = joints[j2_name]
                    if j1.confidence > 0.3 and j2.confidence > 0.3:
                        pt1 = (int(j1.x), int(j1.y))
                        pt2 = (int(j2.x), int(j2.y))
                        cv2.line(frame, pt1, pt2, color_bgr, 3, cv2.LINE_AA)

            for j_name, j in joints.items():
                if j.confidence > 0.3:
                    pt = (int(j.x), int(j.y))
                    cv2.circle(frame, pt, 5, (255, 255, 255), 1, cv2.LINE_AA)
                    cv2.circle(frame, pt, 4, color_bgr, -1, cv2.LINE_AA)

        for lbox in placed_label_boxes:
            center_x = (lbox.x_min + lbox.x_max) // 2
            center_y = lbox.y_max if lbox.y_max < lbox.anchor_y else lbox.y_min
            cv2.line(
                frame,
                (center_x, center_y),
                (lbox.anchor_x, lbox.anchor_y),
                lbox.color_bgr,
                1,
                cv2.LINE_AA,
            )

            overlay = frame.copy()
            cv2.rectangle(
                overlay,
                (lbox.x_min, lbox.y_min),
                (lbox.x_max, lbox.y_max),
                (15, 20, 25),
                -1,
            )
            cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)

            cv2.rectangle(
                frame,
                (lbox.x_min, lbox.y_min),
                (lbox.x_max, lbox.y_max),
                lbox.color_bgr,
                2,
            )

            cur_y = lbox.y_min + 16
            for i, line in enumerate(lbox.lines):
                text_color = (255, 255, 255) if i == 0 else lbox.color_bgr
                cv2.putText(
                    frame,
                    line,
                    (lbox.x_min + 8, cur_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    self.font_scale,
                    text_color,
                    self.font_thickness,
                    cv2.LINE_AA,
                )
                cur_y += 18

        return frame, placed_label_boxes


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Skeleton Visualizer & Label Collision Avoidance")
    print("=" * 60)

    vis = SkeletonVisualizer()

    worker_a = WorkerSkeletonVisual(
        worker_id="WRK-ALPHA",
        risk_level="safe",
        rula_score=2,
        sustained_seconds=0.0,
        joints={
            "nose": Joint2D(x=200, y=200),
            "neck": Joint2D(x=200, y=230),
            "left_shoulder": Joint2D(x=175, y=240),
            "right_shoulder": Joint2D(x=225, y=240),
        },
    )

    worker_b = WorkerSkeletonVisual(
        worker_id="WRK-BETA",
        risk_level="warning",
        rula_score=4,
        sustained_seconds=45.0,
        joints={
            "nose": Joint2D(x=240, y=205),
            "neck": Joint2D(x=240, y=235),
            "left_shoulder": Joint2D(x=215, y=245),
            "right_shoulder": Joint2D(x=265, y=245),
        },
    )

    worker_c = WorkerSkeletonVisual(
        worker_id="WRK-GAMMA",
        risk_level="critical",
        rula_score=7,
        sustained_seconds=140.0,
        has_active_alert=True,
        joints={
            "nose": Joint2D(x=275, y=200),
            "neck": Joint2D(x=275, y=230),
            "left_shoulder": Joint2D(x=250, y=240),
            "right_shoulder": Joint2D(x=300, y=240),
        },
    )

    placed_boxes: List[LabelBox] = []
    for w in [worker_a, worker_b, worker_c]:
        box = vis.compute_label_box(
            worker=w,
            placed_boxes=placed_boxes,
            frame_width=1280,
            frame_height=720,
        )
        placed_boxes.append(box)

    print(f"Placed {len(placed_boxes)} label boxes for closely-spaced workers:")
    for b in placed_boxes:
        print(f"  Worker {b.worker_id}: bbox=({b.x_min}, {b.y_min}) to ({b.x_max}, {b.y_max}) | size={b.x_max - b.x_min}x{b.y_max - b.y_min}")

    overlap_found = False
    for i in range(len(placed_boxes)):
        for j in range(i + 1, len(placed_boxes)):
            box1 = placed_boxes[i]
            box2 = placed_boxes[j]
            if box1.overlaps(box2, padding=0):
                overlap_found = True
                print(f"COLLISION DETECTED between {box1.worker_id} and {box2.worker_id}!")

    assert not overlap_found, "Label collision detected! Anti-overlap staggering failed."
    print("Verified: ZERO label collisions across all adjacent workers.")
    print("ALL SKELETON VISUALIZER INLINE TESTS PASSED SUCCESSFULLY!")
