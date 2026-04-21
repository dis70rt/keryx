from contextlib import contextmanager
from rich.console import Console
from rich.panel import Panel

console = Console()

class Logger:
    @staticmethod
    def info(msg: str) -> None:
        console.print(f"[cyan][INFO][/cyan] {msg}")

    @staticmethod
    def success(msg: str) -> None:
        console.print(f"  [green][OK][/green] {msg}")

    @staticmethod
    def warn(msg: str) -> None:
        console.print(f"  [yellow][WARN][/yellow] {msg}")

    @staticmethod
    def error(msg: str) -> None:
        console.print(f"  [red][FAIL][/red] {msg}")

    @staticmethod
    def step(msg: str) -> None:
        console.print(f"\n[bold blue][>][/bold blue] {msg}")

    @staticmethod
    def sub_step(msg: str) -> None:
        console.print(f"  [blue][-][/blue] {msg}")

    @staticmethod
    def title(msg: str) -> None:
        console.print()
        console.print(Panel(f"[bold magenta]{msg}[/bold magenta]", expand=False))
        console.print()

    @staticmethod
    def divider() -> None:
        console.rule(style="dim")

    @staticmethod
    def blank() -> None:
        console.print()

    @staticmethod
    @contextmanager
    def status(msg: str):
        with console.status(f"[bold yellow]{msg}[/bold yellow]", spinner="line"):
            yield

logger = Logger()
