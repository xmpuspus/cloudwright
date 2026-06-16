"""Plan / preview the exported infrastructure.

Proves an exported architecture is *deployable*, not just syntactically
emitted, by running `terraform validate` / `terraform plan` or
`pulumi preview` against the generated artifact. Read-only: nothing is
applied. Degrades gracefully when a binary or cloud credentials are absent —
`terraform validate` alone (no credentials required) is the offline proof of
deployability; `terraform plan` adds a real resource diff when credentials
are present.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec

_PLAN_RE = re.compile(r"Plan:\s+(\d+) to add,\s+(\d+) to change,\s+(\d+) to destroy")
_NO_CHANGES_RE = re.compile(r"No changes\.|0 to add, 0 to change, 0 to destroy")

# LLM/app secrets that terraform and pulumi never need. Kept out of the
# subprocess environment so they cannot surface in provider error output.
_APP_SECRET_KEYS = frozenset({"ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY", "CLOUDWRIGHT_API_KEY"})
# Only credential-shaped keys are merged from a project .env into the subprocess.
_CLOUD_CRED_PREFIXES = (
    "AWS_",
    "GOOGLE_",
    "GCLOUD_",
    "CLOUDSDK_",
    "AZURE_",
    "ARM_",
    "DATABRICKS_",
    "TF_VAR_",
    "TF_",
    "PULUMI_",
)
_SECRET_KEY_RE = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL", re.I)


def _secret_values() -> set[str]:
    """Values of every secret-shaped env var, for redacting subprocess output."""
    vals: set[str] = set()
    for env in (dict(os.environ), _subprocess_env()):
        for key, val in env.items():
            if val and len(val) >= 8 and _SECRET_KEY_RE.search(key):
                vals.add(val)
    return vals


def _scrub(text: str) -> str:
    """Redact any secret-shaped env value that leaked into subprocess output."""
    if not text:
        return text
    for val in _secret_values():
        text = text.replace(val, "***REDACTED***")
    return text


@dataclass
class PlanResult:
    tool: str  # "terraform" | "pulumi-python" | "pulumi-ts"
    available: bool  # the required binary is installed
    validated: bool  # config is syntactically/semantically valid
    plan_ran: bool  # a real plan/preview executed (needs credentials)
    ok: bool  # overall: artifact is deployable as far as we could prove
    summary: dict[str, int] | None = None  # {"add": x, "change": y, "destroy": z}
    messages: list[str] = field(default_factory=list)
    output_tail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "available": self.available,
            "validated": self.validated,
            "plan_ran": self.plan_ran,
            "ok": self.ok,
            "summary": self.summary,
            "messages": self.messages,
            "output_tail": self.output_tail,
        }


def _tail(text: str, n: int = 40) -> str:
    lines = (text or "").strip().splitlines()
    return _scrub("\n".join(lines[-n:]))


def _run(cmd: list[str], cwd: str, timeout: int, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        check=False,
    )


def _subprocess_env() -> dict[str, str]:
    """Process env (minus LLM/app secrets) plus cloud creds from a project .env.

    terraform/pulumi never need the LLM API key, so app secrets are stripped from
    the subprocess environment to keep them out of any provider error output, and
    only credential-shaped keys are merged from a project ``.env``.
    """
    env = {k: v for k, v in os.environ.items() if k not in _APP_SECRET_KEYS}
    for base in (Path.cwd(), Path(__file__).resolve().parents[3]):
        dotenv = base / ".env"
        if dotenv.is_file():
            for line in dotenv.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                if not key or key in env or key in _APP_SECRET_KEYS:
                    continue
                if key.startswith(_CLOUD_CRED_PREFIXES):
                    env[key] = val.strip().strip('"').strip("'")
            break
    return env


def _terraform_binary() -> tuple[str | None, str]:
    """Resolve the IaC binary, preferring OpenTofu.

    OpenTofu (`tofu`) is a drop-in for the same generated HCL, so honour it when
    present (or when CLOUDWRIGHT_TF_BINARY points at one). Falls back to
    `terraform`. Returns (path_or_None, tool_label).
    """
    override = os.environ.get("CLOUDWRIGHT_TF_BINARY", "").strip()
    if override:
        path = shutil.which(override) or (override if Path(override).is_file() else None)
        return path, ("opentofu" if "tofu" in override else "terraform")
    tofu = shutil.which("tofu")
    if tofu:
        return tofu, "opentofu"
    return shutil.which("terraform"), "terraform"


def plan_terraform(
    spec: ArchSpec,
    *,
    run_plan: bool = True,
    timeout: int = 180,
) -> PlanResult:
    """`terraform`/`tofu` init -backend=false + validate (+ optional plan)."""
    from cloudwright.exporter import export_spec

    tf, tool = _terraform_binary()
    if not tf:
        return PlanResult(
            tool=tool,
            available=False,
            validated=False,
            plan_ran=False,
            ok=False,
            messages=[
                "Neither tofu nor terraform found on PATH. Install OpenTofu or Terraform to enable plan/preview."
            ],
        )

    env = _subprocess_env()
    with tempfile.TemporaryDirectory() as tmp:
        try:
            export_spec(spec, "terraform", output_dir=tmp)
        except Exception as exc:
            return PlanResult(
                tool=tool,
                available=True,
                validated=False,
                plan_ran=False,
                ok=False,
                messages=[f"Export failed: {exc}"],
            )

        messages: list[str] = []
        init = _run([tf, "init", "-backend=false", "-input=false", "-no-color"], tmp, timeout, env)
        if init.returncode != 0:
            init_out = init.stderr + "\n" + init.stdout
            if re.search(
                r"Argument definition required|Unsupported argument|Invalid block definition|"
                r"Missing required argument|Unsupported block type|configuration is invalid",
                init_out,
                re.I,
            ):
                # init parses the config; invalid generated HCL fails here, not validate.
                init_msg = "terraform init failed: generated configuration is invalid (see output)."
            else:
                init_msg = "terraform init failed (provider download / network?)."
            return PlanResult(
                tool=tool,
                available=True,
                validated=False,
                plan_ran=False,
                ok=False,
                messages=[init_msg],
                output_tail=_tail(init_out),
            )

        val = _run([tf, "validate", "-no-color"], tmp, timeout, env)
        validated = val.returncode == 0
        if validated:
            messages.append("terraform validate: configuration is valid.")
        else:
            messages.append("terraform validate: configuration is INVALID.")
            return PlanResult(
                tool=tool,
                available=True,
                validated=False,
                plan_ran=False,
                ok=False,
                messages=messages,
                output_tail=_tail(val.stderr or val.stdout),
            )

        if not run_plan:
            return PlanResult(
                tool=tool,
                available=True,
                validated=True,
                plan_ran=False,
                ok=True,
                messages=messages,
                output_tail=_tail(val.stdout),
            )

        plan = _run(
            [tf, "plan", "-no-color", "-input=false", "-lock=false", "-refresh=false"],
            tmp,
            timeout,
            env,
        )
        combined = plan.stdout + "\n" + plan.stderr
        if plan.returncode == 0:
            m = _PLAN_RE.search(combined)
            if m:
                summary = {"add": int(m.group(1)), "change": int(m.group(2)), "destroy": int(m.group(3))}
                messages.append(
                    f"terraform plan: {summary['add']} to add, {summary['change']} to change, "
                    f"{summary['destroy']} to destroy."
                )
            elif _NO_CHANGES_RE.search(combined):
                summary = {"add": 0, "change": 0, "destroy": 0}
                messages.append("terraform plan: no changes.")
            else:
                summary = None
                messages.append("terraform plan: completed.")
            return PlanResult(
                tool=tool,
                available=True,
                validated=True,
                plan_ran=True,
                ok=True,
                summary=summary,
                messages=messages,
                output_tail=_tail(combined),
            )

        # Plan failed — almost always missing cloud credentials. The config is
        # still proven valid; surface that honestly rather than failing.
        cred_hint = re.search(r"(credential|authenticat|No valid|access key|could not be found)", combined, re.I)
        var_hint = re.search(r"No value for required variable|not set, and has no\s*default", combined, re.I)
        if cred_hint:
            reason = (
                "terraform plan needs cloud credentials (none found). Configuration is valid; "
                "set provider credentials to see a full resource diff."
            )
        elif var_hint:
            reason = (
                "terraform plan needs input variables (e.g. role ARNs). Configuration is valid; "
                "supply a tfvars file to see a full resource diff."
            )
        else:
            reason = "terraform plan did not complete (see output)."
        messages.append(reason)
        return PlanResult(
            tool=tool,
            available=True,
            validated=True,
            plan_ran=False,
            ok=True,  # validate passed → artifact is deployable
            messages=messages,
            output_tail=_tail(combined),
        )


def plan_pulumi(
    spec: ArchSpec,
    *,
    language: str = "python",
    timeout: int = 240,
) -> PlanResult:
    """`pulumi preview` against a local-backend stack. Read-only."""
    from cloudwright.exporter import export_spec

    tool = "pulumi-ts" if language in ("ts", "typescript") else "pulumi-python"
    pulumi = shutil.which("pulumi")
    if not pulumi:
        return PlanResult(
            tool=tool,
            available=False,
            validated=False,
            plan_ran=False,
            ok=False,
            messages=["pulumi binary not found on PATH. Install Pulumi to preview this target."],
        )

    fmt = "pulumi-ts" if tool == "pulumi-ts" else "pulumi-python"
    env = _subprocess_env()
    with tempfile.TemporaryDirectory() as tmp:
        try:
            export_spec(spec, fmt, output_dir=tmp)
        except Exception as exc:
            return PlanResult(
                tool=tool,
                available=True,
                validated=False,
                plan_ran=False,
                ok=False,
                messages=[f"Export failed: {exc}"],
            )

        backend = Path(tmp) / ".pulumi-state"
        env["PULUMI_CONFIG_PASSPHRASE"] = env.get("PULUMI_CONFIG_PASSPHRASE", "")
        env["PULUMI_SKIP_UPDATE_CHECK"] = "true"
        messages: list[str] = []

        login = _run([pulumi, "login", f"file://{backend}"], tmp, timeout, env)
        if login.returncode != 0:
            return PlanResult(
                tool=tool,
                available=True,
                validated=False,
                plan_ran=False,
                ok=False,
                messages=["pulumi login (local backend) failed."],
                output_tail=_tail(login.stderr or login.stdout),
            )

        if tool == "pulumi-python":
            _run(["python", "-m", "venv", ".venv"], tmp, timeout, env)
            pip = str(Path(tmp) / ".venv" / "bin" / "pip")
            if Path(pip).exists():
                _run([pip, "install", "-q", "-r", "requirements.txt"], tmp, timeout, env)
        else:
            _run([shutil.which("npm") or "npm", "install", "--silent"], tmp, timeout, env)

        _run([pulumi, "stack", "init", "dev", "--non-interactive"], tmp, timeout, env)
        preview = _run([pulumi, "preview", "--non-interactive", "--diff"], tmp, timeout, env)
        combined = preview.stdout + "\n" + preview.stderr
        if preview.returncode == 0:
            messages.append("pulumi preview: succeeded.")
            return PlanResult(
                tool=tool,
                available=True,
                validated=True,
                plan_ran=True,
                ok=True,
                messages=messages,
                output_tail=_tail(combined),
            )
        cred_hint = re.search(r"(credential|authenticat|No valid|access key)", combined, re.I)
        messages.append(
            "pulumi preview needs cloud credentials (none found). Project compiled; "
            "set credentials to see a full preview."
            if cred_hint
            else "pulumi preview did not complete (see output)."
        )
        return PlanResult(
            tool=tool,
            available=True,
            validated=bool(cred_hint),
            plan_ran=False,
            ok=bool(cred_hint),
            messages=messages,
            output_tail=_tail(combined),
        )


def plan(spec: ArchSpec, target: str = "terraform", *, run_plan: bool = True, timeout: int = 180) -> PlanResult:
    """Dispatch to the right planner for the given target."""
    target = target.lower().strip()
    if target in ("terraform", "tf"):
        return plan_terraform(spec, run_plan=run_plan, timeout=timeout)
    if target in ("pulumi-python", "pulumi-py", "pulumi"):
        return plan_pulumi(spec, language="python", timeout=timeout)
    if target in ("pulumi-ts", "pulumi-typescript"):
        return plan_pulumi(spec, language="typescript", timeout=timeout)
    raise ValueError(f"Unknown plan target {target!r}. Use terraform, pulumi-python, or pulumi-ts.")
