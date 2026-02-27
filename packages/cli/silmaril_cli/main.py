import typer

from silmaril_cli.commands.catalog_cmd import catalog_app
from silmaril_cli.commands.chat import chat
from silmaril_cli.commands.compare import compare
from silmaril_cli.commands.cost import cost
from silmaril_cli.commands.design import design
from silmaril_cli.commands.diff import diff
from silmaril_cli.commands.export import export
from silmaril_cli.commands.validate import validate

app = typer.Typer(
    name="silmaril",
    help="Architecture intelligence for cloud engineers",
    no_args_is_help=True,
)

app.command()(design)
app.command()(cost)
app.command()(compare)
app.command()(validate)
app.command()(export)
app.command()(diff)
app.command()(chat)
app.add_typer(catalog_app, name="catalog")
