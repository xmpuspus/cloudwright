import typer

from cloudwright_cli import __version__
from cloudwright_cli.commands.analyze_cmd import analyze
from cloudwright_cli.commands.catalog_cmd import catalog_app
from cloudwright_cli.commands.chat import chat
from cloudwright_cli.commands.compare import compare
from cloudwright_cli.commands.cost import cost
from cloudwright_cli.commands.design import design
from cloudwright_cli.commands.diff import diff
from cloudwright_cli.commands.drift_cmd import drift
from cloudwright_cli.commands.export import export
from cloudwright_cli.commands.import_cmd import import_infra
from cloudwright_cli.commands.init_cmd import init
from cloudwright_cli.commands.lint_cmd import lint
from cloudwright_cli.commands.modify_cmd import modify
from cloudwright_cli.commands.policy import policy
from cloudwright_cli.commands.refresh_cmd import refresh
from cloudwright_cli.commands.score_cmd import score
from cloudwright_cli.commands.validate import validate


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
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["json"] = json_output


app.command()(design)
app.command()(cost)
app.command()(compare)
app.command()(validate)
app.command()(export)
app.command()(diff)
app.command()(drift)
app.command()(modify)
app.command(name="import")(import_infra)
app.command()(chat)
app.command()(init)
app.command()(policy)
app.command()(score)
app.command()(analyze)
app.command()(refresh)
app.command()(lint)
app.add_typer(catalog_app, name="catalog")
