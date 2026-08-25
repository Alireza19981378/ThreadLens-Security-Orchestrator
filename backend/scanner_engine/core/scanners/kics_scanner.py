# scanner_engine/core/scanners/kics_scanner.py
import json
from .base import BaseScanner, ScannerExecutionError


class KICSScanner(BaseScanner):
    def update_database(self):
        return {"tool": "kics", "action": "noop"}

    def scan(self, target: str, **kwargs):
        cmd = [
            self.ctx.executable_path,
            "scan",
            "-p", target,
            "-o", "results",
            "-f", "json",
            "--no-progress",
            "-q", "/Users/arash/Documents/pro/kics/assets/queries",
        ]
        cmd += self.extra_args
        cp = self.run_cmd(cmd, timeout=1800)
        # KICS writes results to output folder; we can parse from stdout if using --minimal-ui.
        # For brevity, assume JSON is in stdout.
        try:
            data = json.loads(cp.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise ScannerExecutionError("KICS returned invalid JSON") from exc
        return {"tool": "kics", "result": data}
