"""Public KDE Plasma 6 panel live editing interface using D-Bus scripting and configuration persistence."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PanelHidingMode(str, Enum):
    """Supported panel auto-hide and overlay visibility behaviors in KDE Plasma 6."""

    ALWAYS_VISIBLE = "always_visible"
    AUTO_HIDE = "auto_hide"
    DODGE_WINDOWS = "dodge_windows"
    WINDOWS_GO_BELOW = "windows_go_below"


# Mapping from user-friendly visibility names to KDE Plasma JavaScript hiding property strings
VISIBILITY_NAME_TO_SCRIPT: Dict[str, str] = {
    "always_visible": "none",
    "auto_hide": "autohide",
    "dodge_windows": "dodgewindows",
    "windows_go_below": "windowsgobelow",
}

# Mapping from KDE Plasma JavaScript hiding strings to user-friendly visibility names
VISIBILITY_SCRIPT_TO_NAME: Dict[str, str] = {
    "none": "always_visible",
    "normal": "always_visible",
    "autohide": "auto_hide",
    "dodgewindows": "dodge_windows",
    "windowsgobelow": "windows_go_below",
}

# Mapping between visibility names and desktop-appletsrc configuration integer codes
VISIBILITY_NAME_TO_CODE: Dict[str, int] = {
    "always_visible": 0,
    "auto_hide": 1,
    "dodge_windows": 2,
    "windows_go_below": 3,
}

VISIBILITY_CODE_TO_NAME: Dict[int, str] = {
    0: "always_visible",
    1: "auto_hide",
    2: "dodge_windows",
    3: "windows_go_below",
}

VALID_POSITIONS = {"top", "bottom", "left", "right"}


class KdePanelLiveEditor:
    """Safely manages live KDE Plasma 6 panel properties via org.kde.PlasmaShell evaluateScript."""

    def __init__(self, qdbus_bin: Optional[str] = None) -> None:
        self.qdbus_bin = qdbus_bin if qdbus_bin is not None else (shutil.which("qdbus6") or shutil.which("qdbus"))
        self.timeout_seconds = 2.0

    def execute_script(self, script: str) -> Tuple[bool, str, str]:
        """Execute a JavaScript snippet inside running PlasmaShell via evaluateScript.

        Returns:
            (success, stdout_str, stderr_or_error_str)
        """
        if not self.qdbus_bin:
            return False, "", "qdbus utility not found on host system."

        try:
            res = subprocess.run(
                [self.qdbus_bin, "org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.evaluateScript", script],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            if res.returncode != 0:
                err_text = res.stderr.strip() or f"Process exited with code {res.returncode}"
                return False, "", err_text
            return True, res.stdout.strip(), ""
        except subprocess.TimeoutExpired:
            return False, "", f"D-Bus evaluation timed out after {self.timeout_seconds}s."
        except Exception as e:
            return False, "", f"Failed to execute D-Bus script: {e}"

    def is_live_dbus_supported(self) -> bool:
        """Check if qdbus is available and PlasmaShell D-Bus interface responds."""
        if not self.qdbus_bin:
            return False

        ok, out, _ = self.execute_script("print('ping');")
        return ok and "ping" in out

    def get_live_panel(self, containment_id: str | int) -> Optional[Dict[str, Any]]:
        """Query live state of a panel containment via D-Bus."""
        if not self.qdbus_bin:
            return None

        try:
            cid_int = int(containment_id)
        except (ValueError, TypeError):
            return None

        script = (
            f"var p = panelById({cid_int});\n"
            f"if (!p) {{\n"
            f"    print(JSON.stringify({{'found': false}}));\n"
            f"}} else {{\n"
            f"    print(JSON.stringify({{\n"
            f"        'found': true,\n"
            f"        'id': String(p.id),\n"
            f"        'location': String(p.location),\n"
            f"        'height': Number(p.height),\n"
            f"        'hiding': String(p.hiding),\n"
            f"        'floating': Boolean(p.floating)\n"
            f"    }}));\n"
            f"}}"
        )

        try:
            ok, out_text, err = self.execute_script(script)
            if not ok or not out_text:
                return None

            data = json.loads(out_text)
            if not data.get("found"):
                return None

            hiding_script = data.get("hiding", "none")
            vis_name = VISIBILITY_SCRIPT_TO_NAME.get(hiding_script, "always_visible")

            return {
                "id": str(data.get("id")),
                "location": str(data.get("location")),
                "height": int(data.get("height", 36)),
                "hiding_raw": hiding_script,
                "visibility": vis_name,
                "floating": bool(data.get("floating", False)),
            }
        except Exception as e:
            logger.warning("Failed to query live panel %s via D-Bus: %s", containment_id, e)
            return None

    def apply_panel_properties(
        self,
        containment_id: str | int,
        location: Optional[str] = None,
        height: Optional[int] = None,
        visibility: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any], str]:
        """Apply supported panel geometry and visibility properties live via D-Bus.
        
        Returns:
            (success, audit_dict, status_message)
            audit_dict contains 'previous' and 'current' states for rollback.
        """
        if not self.qdbus_bin:
            return False, {}, "qdbus utility not found on host system."

        try:
            cid_int = int(containment_id)
        except (ValueError, TypeError):
            return False, {}, f"Invalid panel containment ID: {containment_id}"

        # Parameter validation
        statements: List[str] = []
        if location is not None:
            if location not in VALID_POSITIONS:
                return False, {}, f"Invalid panel position '{location}'. Allowed: {VALID_POSITIONS}"
            statements.append(f"p.location = '{location}';")

        if height is not None:
            if not (16 <= height <= 128):
                return False, {}, f"Panel thickness {height}px out of bounds (16-128px)."
            statements.append(f"p.height = {int(height)};")

        if visibility is not None:
            script_vis = VISIBILITY_NAME_TO_SCRIPT.get(visibility, visibility)
            if script_vis not in VISIBILITY_SCRIPT_TO_NAME:
                return False, {}, f"Invalid panel visibility '{visibility}'. Allowed: {list(VISIBILITY_NAME_TO_SCRIPT.keys())}"
            statements.append(f"p.hiding = '{script_vis}';")

        if not statements:
            return True, {}, "No property modifications requested."

        apply_code = "\n    ".join(statements)

        script = (
            f"var p = panelById({cid_int});\n"
            f"if (!p) {{\n"
            f"    print(JSON.stringify({{'success': false, 'error': 'Panel containment #{cid_int} not found in running Plasma session'}}));\n"
            f"}} else {{\n"
            f"    var prev = {{\n"
            f"        'id': String(p.id),\n"
            f"        'location': String(p.location),\n"
            f"        'height': Number(p.height),\n"
            f"        'hiding': String(p.hiding),\n"
            f"        'floating': Boolean(p.floating)\n"
            f"    }};\n"
            f"    {apply_code}\n"
            f"    var curr = {{\n"
            f"        'id': String(p.id),\n"
            f"        'location': String(p.location),\n"
            f"        'height': Number(p.height),\n"
            f"        'hiding': String(p.hiding),\n"
            f"        'floating': Boolean(p.floating)\n"
            f"    }};\n"
            f"    print(JSON.stringify({{'success': true, 'previous': prev, 'current': curr}}));\n"
            f"}}"
        )

        try:
            ok, out_text, err_text = self.execute_script(script)
            if not ok:
                return False, {}, f"D-Bus script evaluation failed: {err_text}"

            if not out_text:
                return False, {}, "D-Bus script returned empty response."

            data = json.loads(out_text)
            if not data.get("success"):
                return False, {}, data.get("error", "Unknown script error")

            prev_state = data.get("previous", {})
            curr_state = data.get("current", {})

            # Map raw script hiding back to friendly names
            if "hiding" in prev_state:
                prev_state["visibility"] = VISIBILITY_SCRIPT_TO_NAME.get(prev_state["hiding"], "always_visible")
            if "hiding" in curr_state:
                curr_state["visibility"] = VISIBILITY_SCRIPT_TO_NAME.get(curr_state["hiding"], "always_visible")

            return (
                True,
                {"previous": prev_state, "current": curr_state},
                f"Panel #{containment_id} updated live via D-Bus.",
            )

        except json.JSONDecodeError as e:
            return False, {}, f"Failed to parse D-Bus script JSON response: {e}"
        except Exception as e:
            return False, {}, f"Unexpected error applying live panel properties: {e}"

    def revert_panel_properties(
        self,
        containment_id: str | int,
        previous_state: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """Revert panel properties back to the recorded previous state and verify restoration."""
        if not previous_state:
            return True, "No previous state recorded to revert."

        loc = previous_state.get("location")
        height = previous_state.get("height")
        hiding = previous_state.get("hiding") or previous_state.get("visibility")

        success, audit, msg = self.apply_panel_properties(
            containment_id=containment_id,
            location=loc,
            height=height,
            visibility=hiding,
        )

        if not success:
            return False, f"Live rollback failed on panel #{containment_id}: {msg}"

        # Verify restoration
        current = audit.get("current", {})
        if loc and current.get("location") != loc:
            return False, f"Post-revert location mismatch: expected '{loc}', got '{current.get('location')}'"
        if height and abs(current.get("height", 0) - height) > 2:
            return False, f"Post-revert height mismatch: expected {height}px, got {current.get('height')}px"

        return True, f"Live rollback verified on panel #{containment_id}."

    def verify_panel_properties(
        self,
        containment_id: str | int,
        expected_location: Optional[str] = None,
        expected_height: Optional[int] = None,
        expected_visibility: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Verify that live panel properties on the running desktop match expected values."""
        live_panel = self.get_live_panel(containment_id)
        if not live_panel:
            return False, f"Panel #{containment_id} not found in running desktop session."

        if expected_location is not None:
            if live_panel.get("location") != expected_location:
                return (
                    False,
                    f"Location verification failed on panel #{containment_id}: expected '{expected_location}', got '{live_panel.get('location')}'",
                )

        if expected_height is not None:
            # Allow minor Qt layout rounding margin of 2px
            live_h = live_panel.get("height", 0)
            if abs(live_h - expected_height) > 2:
                return (
                    False,
                    f"Height verification failed on panel #{containment_id}: expected {expected_height}px, got {live_h}px",
                )

        if expected_visibility is not None:
            script_expected = VISIBILITY_NAME_TO_SCRIPT.get(expected_visibility, expected_visibility)
            live_hiding = live_panel.get("hiding_raw") or live_panel.get("hiding") or VISIBILITY_NAME_TO_SCRIPT.get(live_panel.get("visibility", ""), "")
            if live_hiding != script_expected:
                return (
                    False,
                    f"Visibility verification failed on panel #{containment_id}: expected '{expected_visibility}' ('{script_expected}'), got '{live_hiding}'",
                )

        return True, f"Live panel #{containment_id} verified successfully."
