"""
rula_assessment.py
Implements the Rapid Upper Limb Assessment (RULA) ergonomic standard (McAtamney & Corlett 1993).
Fully deterministic assessment converting stereo-vision tracked human joint angles and modifiers into
component scores, posture scores A & B, wrist/arm & neck/trunk scores C & D, and a 1-7 final score.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, Tuple


class RiskLevel(str, Enum):
    SAFE = "safe"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ComponentScores:
    """Detailed breakdown of individual body part scores and modifiers."""
    upper_arm_base: int
    upper_arm_modifier: int
    upper_arm_total: int

    lower_arm_base: int
    lower_arm_modifier: int
    lower_arm_total: int

    wrist_base: int
    wrist_modifier: int
    wrist_total: int

    wrist_twist: int

    table_a_score: int
    muscle_use_a: int
    force_load_a: int
    score_c: int

    neck_base: int
    neck_modifier: int
    neck_total: int

    trunk_base: int
    trunk_modifier: int
    trunk_total: int

    legs: int

    table_b_score: int
    muscle_use_b: int
    force_load_b: int
    score_d: int


@dataclass(frozen=True)
class RULAResult:
    """Structured result of a RULA ergonomic assessment."""
    final_score: int                 # 1 to 7
    action_level: int                # 1 to 4
    action_description: str          # Descriptive clinical recommendation
    risk_level: RiskLevel            # "safe" | "warning" | "critical"
    components: ComponentScores      # Granular component scores
    raw_angles: Dict[str, float]     # Joint flexion angles in degrees
    raw_modifiers: Dict[str, bool]   # Posture modifiers (twisted, raised, abducted, etc.)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "final_score": self.final_score,
            "action_level": self.action_level,
            "action_description": self.action_description,
            "risk_level": self.risk_level.value,
            "components": {
                "upper_arm": self.components.upper_arm_total,
                "lower_arm": self.components.lower_arm_total,
                "wrist": self.components.wrist_total,
                "wrist_twist": self.components.wrist_twist,
                "table_a_score": self.components.table_a_score,
                "score_c": self.components.score_c,
                "neck": self.components.neck_total,
                "trunk": self.components.trunk_total,
                "legs": self.components.legs,
                "table_b_score": self.components.table_b_score,
                "score_d": self.components.score_d,
            },
            "raw_angles": self.raw_angles,
            "raw_modifiers": self.raw_modifiers,
        }


class RULAAssessment:
    """
    Rapid Upper Limb Assessment (RULA) calculator.
    Standardized according to McAtamney, L., & Corlett, E. N. (1993).
    """

    # Table A: (Upper Arm: 1-6) x (Lower Arm: 1-3) x (Wrist: 1-4) x (Wrist Twist: 1-2) -> Score A
    # Indexed as TABLE_A[upper_arm - 1][lower_arm - 1][wrist - 1][wrist_twist - 1]
    TABLE_A: Tuple[Tuple[Tuple[Tuple[int, ...], ...], ...], ...] = (
        # Upper Arm = 1
        (
            # Lower Arm = 1
            ((1, 2), (2, 2), (2, 3), (3, 3)),  # Wrist 1, 2, 3, 4
            # Lower Arm = 2
            ((2, 2), (2, 2), (3, 3), (3, 3)),
            # Lower Arm = 3
            ((2, 3), (3, 3), (3, 3), (4, 4)),
        ),
        # Upper Arm = 2
        (
            # Lower Arm = 1
            ((2, 3), (3, 3), (3, 4), (4, 4)),
            # Lower Arm = 2
            ((3, 3), (3, 3), (3, 4), (4, 4)),
            # Lower Arm = 3
            ((3, 4), (4, 4), (4, 4), (5, 5)),
        ),
        # Upper Arm = 3
        (
            # Lower Arm = 1
            ((3, 3), (4, 4), (4, 4), (5, 5)),
            # Lower Arm = 2
            ((3, 4), (4, 4), (4, 4), (5, 5)),
            # Lower Arm = 3
            ((4, 4), (4, 4), (5, 5), (5, 5)),
        ),
        # Upper Arm = 4
        (
            # Lower Arm = 1
            ((4, 4), (4, 5), (5, 5), (5, 6)),
            # Lower Arm = 2
            ((4, 4), (4, 5), (5, 5), (5, 6)),
            # Lower Arm = 3
            ((4, 5), (5, 5), (5, 6), (6, 6)),
        ),
        # Upper Arm = 5
        (
            # Lower Arm = 1
            ((5, 5), (5, 6), (6, 7), (7, 7)),
            # Lower Arm = 2
            ((5, 6), (6, 6), (6, 7), (7, 7)),
            # Lower Arm = 3
            ((6, 6), (6, 7), (7, 7), (7, 8)),
        ),
        # Upper Arm = 6
        (
            # Lower Arm = 1
            ((7, 7), (7, 7), (7, 8), (8, 8)),
            # Lower Arm = 2
            ((8, 8), (8, 8), (8, 8), (8, 9)),
            # Lower Arm = 3
            ((9, 9), (9, 9), (9, 9), (9, 9)),
        ),
    )

    # Table B: (Neck: 1-6) x (Trunk: 1-6) x (Legs: 1-2) -> Score B
    # Indexed as TABLE_B[neck - 1][trunk - 1][legs - 1]
    TABLE_B: Tuple[Tuple[Tuple[int, ...], ...], ...] = (
        # Neck = 1
        (
            (1, 3), (2, 3), (3, 4), (5, 5), (6, 6), (7, 7)  # Trunk 1..6
        ),
        # Neck = 2
        (
            (2, 3), (2, 3), (4, 5), (5, 5), (6, 7), (7, 7)
        ),
        # Neck = 3
        (
            (3, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 7)
        ),
        # Neck = 4
        (
            (5, 5), (5, 6), (6, 7), (7, 7), (7, 7), (8, 8)
        ),
        # Neck = 5
        (
            (6, 6), (6, 7), (7, 7), (7, 8), (8, 8), (8, 8)
        ),
        # Neck = 6
        (
            (7, 7), (7, 7), (7, 8), (8, 8), (8, 9), (9, 9)
        ),
    )

    # Table C: Score C (row 1..8+) x Score D (col 1..7+) -> Grand Score (1..7)
    TABLE_C: Tuple[Tuple[int, ...], ...] = (
        # Score C = 1
        (1, 2, 3, 3, 4, 5, 5),
        # Score C = 2
        (2, 2, 3, 4, 4, 5, 5),
        # Score C = 3
        (3, 3, 3, 4, 4, 5, 6),
        # Score C = 4
        (3, 3, 3, 4, 5, 6, 6),
        # Score C = 5
        (4, 4, 4, 5, 6, 7, 7),
        # Score C = 6
        (4, 4, 5, 6, 6, 7, 7),
        # Score C = 7
        (5, 5, 6, 6, 7, 7, 7),
        # Score C = 8+
        (5, 5, 6, 7, 7, 7, 7),
    )

    @classmethod
    def score_upper_arm(
        cls,
        flexion_deg: float,
        shoulder_raised: bool = False,
        arm_abducted: bool = False,
        arm_supported: bool = False,
    ) -> Tuple[int, int, int]:
        """
        Calculate Upper Arm score (1 to 6).
        Flexion angles:
          -20° to 20°: 1
          <-20° (extension) or 20° to 45°: 2
          45° to 90°: 3
          >90°: 4
        Modifiers:
          +1 raised shoulder, +1 arm abducted, -1 arm supported
        """
        if -20.0 <= flexion_deg <= 20.0:
            base = 1
        elif flexion_deg < -20.0 or (20.0 < flexion_deg <= 45.0):
            base = 2
        elif 45.0 < flexion_deg <= 90.0:
            base = 3
        else:  # > 90.0
            base = 4

        modifier = 0
        if shoulder_raised:
            modifier += 1
        if arm_abducted:
            modifier += 1
        if arm_supported:
            modifier -= 1

        total = max(1, min(6, base + modifier))
        return base, modifier, total

    @classmethod
    def score_lower_arm(
        cls,
        flexion_deg: float,
        working_across_midline_or_side: bool = False,
    ) -> Tuple[int, int, int]:
        """
        Calculate Lower Arm score (1 to 3).
        Flexion:
          60° to 100°: 1 (neutral)
          <60° or >100°: 2
        Modifiers:
          +1 if working across midline or out to side
        """
        if 60.0 <= flexion_deg <= 100.0:
            base = 1
        else:
            base = 2

        modifier = 1 if working_across_midline_or_side else 0
        total = max(1, min(3, base + modifier))
        return base, modifier, total

    @classmethod
    def score_wrist(
        cls,
        flexion_deg: float,
        wrist_bent_away_midline: bool = False,
        wrist_twist_near_end: bool = False,
    ) -> Tuple[int, int, int, int]:
        """
        Calculate Wrist (1 to 4) and Wrist Twist (1 to 2) scores.
        Flexion:
          0° (neutral within ±5°): 1
          0° to 15° (or -15° to 0°): 2
          >15° or <-15°: 3
        Modifiers:
          +1 if wrist is bent away from midline (radial/ulnar deviation)
        Wrist twist:
          1 if mid-range, 2 if near end of range
        """
        abs_flex = abs(flexion_deg)
        if abs_flex <= 5.0:
            base = 1
        elif abs_flex <= 15.0:
            base = 2
        else:
            base = 3

        modifier = 1 if wrist_bent_away_midline else 0
        wrist_total = max(1, min(4, base + modifier))
        wrist_twist = 2 if wrist_twist_near_end else 1
        return base, modifier, wrist_total, wrist_twist

    @classmethod
    def score_neck(
        cls,
        flexion_deg: float,
        twisted: bool = False,
        side_bending: bool = False,
    ) -> Tuple[int, int, int]:
        """
        Calculate Neck score (1 to 6).
        Flexion:
          0° to 10°: 1
          10° to 20°: 2
          >20°: 3
          <0° (extension / backwards): 4
        Modifiers:
          +1 if neck twisted, +1 if side-bending
        """
        if flexion_deg < 0.0:
            base = 4  # neck in extension
        elif flexion_deg <= 10.0:
            base = 1
        elif flexion_deg <= 20.0:
            base = 2
        else:
            base = 3

        modifier = 0
        if twisted:
            modifier += 1
        if side_bending:
            modifier += 1

        total = max(1, min(6, base + modifier))
        return base, modifier, total

    @classmethod
    def score_trunk(
        cls,
        flexion_deg: float,
        twisted: bool = False,
        side_bending: bool = False,
    ) -> Tuple[int, int, int]:
        """
        Calculate Trunk score (1 to 6).
        Flexion:
          0° (neutral, seated/upright): 1
          0° to 20°: 2
          20° to 60°: 3
          >60°: 4
        Modifiers:
          +1 if trunk twisted, +1 if side-bending
        """
        if flexion_deg <= 5.0:
            base = 1
        elif flexion_deg <= 20.0:
            base = 2
        elif flexion_deg <= 60.0:
            base = 3
        else:
            base = 4

        modifier = 0
        if twisted:
            modifier += 1
        if side_bending:
            modifier += 1

        total = max(1, min(6, base + modifier))
        return base, modifier, total

    @classmethod
    def score_legs(cls, supported_and_balanced: bool = True) -> int:
        """Legs: 1 if supported and balanced, 2 if not."""
        return 1 if supported_and_balanced else 2

    @classmethod
    def evaluate(
        cls,
        shoulder_flexion: float = 10.0,
        elbow_flexion: float = 90.0,
        wrist_flexion: float = 0.0,
        neck_flexion: float = 5.0,
        trunk_flexion: float = 0.0,
        shoulder_raised: bool = False,
        arm_abducted: bool = False,
        arm_supported: bool = False,
        arm_across_midline: bool = False,
        wrist_deviation: bool = False,
        wrist_twist_end: bool = False,
        neck_twisted: bool = False,
        neck_side_bend: bool = False,
        trunk_twisted: bool = False,
        trunk_side_bend: bool = False,
        legs_balanced: bool = True,
        muscle_use: int = 0,  # 0 or 1 (+1 if static > 1 min or repetitive > 4x/min)
        force_load: int = 0,  # 0: <2kg intermittent, 1: 2-10kg intermittent, 2: 2-10kg static/repetitive, 3: >10kg / shock
    ) -> RULAResult:
        """
        Compute full RULA assessment deterministically.
        Returns complete RULAResult dataclass.
        """
        # Upper Arm
        ua_base, ua_mod, ua_tot = cls.score_upper_arm(
            shoulder_flexion, shoulder_raised, arm_abducted, arm_supported
        )
        # Lower Arm
        la_base, la_mod, la_tot = cls.score_lower_arm(
            elbow_flexion, arm_across_midline
        )
        # Wrist & Twist
        w_base, w_mod, w_tot, w_twist = cls.score_wrist(
            wrist_flexion, wrist_deviation, wrist_twist_end
        )

        # Table A Lookup
        # Clamp indices to valid table dimensions
        idx_ua = max(0, min(5, ua_tot - 1))
        idx_la = max(0, min(2, la_tot - 1))
        idx_w = max(0, min(3, w_tot - 1))
        idx_wt = max(0, min(1, w_twist - 1))
        table_a_score = cls.TABLE_A[idx_ua][idx_la][idx_w][idx_wt]

        # Score C = Table A + Muscle Use A + Force/Load A
        score_c = table_a_score + muscle_use + force_load

        # Neck
        neck_base, neck_mod, neck_tot = cls.score_neck(
            neck_flexion, neck_twisted, neck_side_bend
        )
        # Trunk
        trunk_base, trunk_mod, trunk_tot = cls.score_trunk(
            trunk_flexion, trunk_twisted, trunk_side_bend
        )
        # Legs
        legs_score = cls.score_legs(legs_balanced)

        # Table B Lookup
        idx_neck = max(0, min(5, neck_tot - 1))
        idx_trunk = max(0, min(5, trunk_tot - 1))
        idx_legs = max(0, min(1, legs_score - 1))
        table_b_score = cls.TABLE_B[idx_neck][idx_trunk][idx_legs]

        # Score D = Table B + Muscle Use B + Force/Load B
        score_d = table_b_score + muscle_use + force_load

        # Table C Lookup: row = score_c (1..8+), col = score_d (1..7+)
        idx_c = max(0, min(7, score_c - 1))
        idx_d = max(0, min(6, score_d - 1))
        final_score = cls.TABLE_C[idx_c][idx_d]

        # Map to Action Levels and Risk Level
        if final_score in (1, 2):
            action_level = 1
            action_desc = "Acceptable posture if not maintained or repeated for long periods."
            risk_lvl = RiskLevel.SAFE
        elif final_score in (3, 4):
            action_level = 2
            action_desc = "Further investigation needed; posture modifications may be required."
            risk_lvl = RiskLevel.WARNING
        elif final_score in (5, 6):
            action_level = 3
            action_desc = "Investigation and ergonomic changes required soon."
            risk_lvl = RiskLevel.WARNING
        else:  # final_score == 7 (or above)
            action_level = 4
            action_desc = "Immediate investigation and ergonomic changes required to prevent musculoskeletal injury."
            risk_lvl = RiskLevel.CRITICAL

        components = ComponentScores(
            upper_arm_base=ua_base,
            upper_arm_modifier=ua_mod,
            upper_arm_total=ua_tot,
            lower_arm_base=la_base,
            lower_arm_modifier=la_mod,
            lower_arm_total=la_tot,
            wrist_base=w_base,
            wrist_modifier=w_mod,
            wrist_total=w_tot,
            wrist_twist=w_twist,
            table_a_score=table_a_score,
            muscle_use_a=muscle_use,
            force_load_a=force_load,
            score_c=score_c,
            neck_base=neck_base,
            neck_modifier=neck_mod,
            neck_total=neck_tot,
            trunk_base=trunk_base,
            trunk_modifier=trunk_mod,
            trunk_total=trunk_tot,
            legs=legs_score,
            table_b_score=table_b_score,
            muscle_use_b=muscle_use,
            force_load_b=force_load,
            score_d=score_d,
        )

        raw_angles = {
            "shoulder_flexion": shoulder_flexion,
            "elbow_flexion": elbow_flexion,
            "wrist_flexion": wrist_flexion,
            "neck_flexion": neck_flexion,
            "trunk_flexion": trunk_flexion,
        }

        raw_modifiers = {
            "shoulder_raised": shoulder_raised,
            "arm_abducted": arm_abducted,
            "arm_supported": arm_supported,
            "arm_across_midline": arm_across_midline,
            "wrist_deviation": wrist_deviation,
            "wrist_twist_end": wrist_twist_end,
            "neck_twisted": neck_twisted,
            "neck_side_bend": neck_side_bend,
            "trunk_twisted": trunk_twisted,
            "trunk_side_bend": trunk_side_bend,
            "legs_balanced": legs_balanced,
        }

        return RULAResult(
            final_score=final_score,
            action_level=action_level,
            action_description=action_desc,
            risk_level=risk_lvl,
            components=components,
            raw_angles=raw_angles,
            raw_modifiers=raw_modifiers,
        )


if __name__ == "__main__":
    print("=" * 60)
    print("Testing RULA Assessment Module (McAtamney & Corlett 1993)")
    print("=" * 60)

    # 1. Neutral posture -> must score SAFE (1-2)
    neutral = RULAAssessment.evaluate(
        shoulder_flexion=10.0,
        elbow_flexion=90.0,
        wrist_flexion=0.0,
        neck_flexion=5.0,
        trunk_flexion=0.0,
        legs_balanced=True,
    )
    print(f"Neutral Posture: Final Score={neutral.final_score}, Risk Level={neutral.risk_level.value}, Action Level={neutral.action_level}")
    assert neutral.risk_level == RiskLevel.SAFE, f"Expected SAFE, got {neutral.risk_level}"
    assert neutral.final_score in (1, 2), f"Expected 1 or 2, got {neutral.final_score}"

    # 2. Moderate posture -> must score WARNING (3-6)
    moderate = RULAAssessment.evaluate(
        shoulder_flexion=50.0,
        elbow_flexion=110.0,
        wrist_flexion=12.0,
        neck_flexion=18.0,
        trunk_flexion=25.0,
        arm_abducted=True,
    )
    print(f"Moderate Posture: Final Score={moderate.final_score}, Risk Level={moderate.risk_level.value}, Action Level={moderate.action_level}")
    assert moderate.risk_level == RiskLevel.WARNING, f"Expected WARNING, got {moderate.risk_level}"
    assert 3 <= moderate.final_score <= 6, f"Expected 3-6, got {moderate.final_score}"
    assert neutral.final_score < moderate.final_score, "Moderate score must be strictly greater than neutral score"

    # 3. Severe awkward posture -> must score CRITICAL (7)
    severe = RULAAssessment.evaluate(
        shoulder_flexion=105.0,
        elbow_flexion=130.0,
        wrist_flexion=28.0,
        neck_flexion=35.0,
        trunk_flexion=70.0,
        shoulder_raised=True,
        arm_abducted=True,
        wrist_deviation=True,
        wrist_twist_end=True,
        neck_twisted=True,
        trunk_twisted=True,
        legs_balanced=False,
        force_load=2,
        muscle_use=1,
    )
    print(f"Severe Posture: Final Score={severe.final_score}, Risk Level={severe.risk_level.value}, Action Level={severe.action_level}")
    assert severe.risk_level == RiskLevel.CRITICAL, f"Expected CRITICAL, got {severe.risk_level}"
    assert severe.final_score == 7, f"Expected 7, got {severe.final_score}"
    assert moderate.final_score < severe.final_score, "Severe score must be strictly greater than moderate score"

    print("ALL RULA ASSESSMENT INLINE TESTS PASSED SUCCESSFULLY!")
