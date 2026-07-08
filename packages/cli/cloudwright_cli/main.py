import typer

from cloudwright_cli import __version__
from cloudwright_cli.commands.adr import adr
from cloudwright_cli.commands.analyze_cmd import analyze
from cloudwright_cli.commands.catalog_cmd import catalog_app
from cloudwright_cli.commands.chat import chat
from cloudwright_cli.commands.compare import compare
from cloudwright_cli.commands.compliance_cmd import compliance_scan
from cloudwright_cli.commands.cost import cost
from cloudwright_cli.commands.databricks_cmd import databricks_validate
from cloudwright_cli.commands.design import design
from cloudwright_cli.commands.diff import diff
from cloudwright_cli.commands.drift_cmd import drift
from cloudwright_cli.commands.export import export
from cloudwright_cli.commands.import_cmd import import_infra
from cloudwright_cli.commands.import_live_cmd import import_live
from cloudwright_cli.commands.init_cmd import init
from cloudwright_cli.commands.lint_cmd import lint
from cloudwright_cli.commands.mcp_cmd import mcp_serve
from cloudwright_cli.commands.modify_cmd import modify
from cloudwright_cli.commands.plan_cmd import plan
from cloudwright_cli.commands.policy import policy
from cloudwright_cli.commands.refresh_cmd import refresh
from cloudwright_cli.commands.review_cmd import review
from cloudwright_cli.commands.schema_cmd import schema
from cloudwright_cli.commands.score_cmd import score
from cloudwright_cli.commands.security_cmd import security_scan
from cloudwright_cli.commands.validate import validate
from cloudwright_cli.decorators import cloudwright_command


def _version_callback(value: bool) -> None:
    if value:
        print(f"cloudwright {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="cloudwright",
    help="Architecture intelligence for cloud engineers",
    no_args_is_help=True,
)


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-V", help="Show version", callback=_version_callback, is_eager=True
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview LLM operations without calling the API"),
    stream: bool = typer.Option(False, "--stream", help="NDJSON streaming output (one JSON line per item)"),
) -> None:
    from cloudwright.logging import configure_logging

    configure_logging()
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["json"] = json_output
    ctx.obj["dry_run"] = dry_run
    ctx.obj["stream"] = stream


app.command()(cloudwright_command()(design))
app.command()(cloudwright_command()(cost))
app.command()(cloudwright_command()(compare))
app.command()(cloudwright_command()(validate))
app.command()(cloudwright_command()(export))
app.command()(cloudwright_command()(diff))
app.command()(cloudwright_command()(drift))
app.command()(cloudwright_command()(modify))
app.command(name="import")(cloudwright_command()(import_infra))
app.command(name="import-live")(cloudwright_command()(import_live))
app.command()(cloudwright_command()(chat))
app.command()(cloudwright_command()(init))
app.command()(cloudwright_command()(plan))
app.command()(cloudwright_command()(policy))
app.command()(cloudwright_command()(score))
app.command()(cloudwright_command()(review))
app.command()(cloudwright_command()(analyze))
app.command()(cloudwright_command()(refresh))
app.command()(cloudwright_command()(lint))
app.command()(cloudwright_command()(databricks_validate))
app.command(name="security")(cloudwright_command()(security_scan))
app.command(name="compliance")(cloudwright_command()(compliance_scan))
app.command(name="adr")(cloudwright_command()(adr))
app.command()(cloudwright_command()(schema))
app.command(name="mcp")(cloudwright_command()(mcp_serve))
app.add_typer(catalog_app, name="catalog")
