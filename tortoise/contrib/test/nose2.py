import logging

from nose2.events import Event, Plugin

from tortoise.contrib.test import finalizer, initializer

log = logging.getLogger("nose2.plugins.tortoise")


class TortoisePlugin(Plugin):  # type: ignore
    # pylint: disable=E1101
    configSection = "tortoise"
    alwaysOn = True

    def __init__(self) -> None:
        self.db_url = self.config.as_str("db-url", "").strip() or "sqlite://:memory:"
        self.db_modules = self.config.as_list("db-module", [])
        if not self.db_modules:
            self.alwaysOn = False

        group = self.session.pluginargs
        group.add_argument(
            "--db-module",
            action="append",
            default=[],
            metavar="MODULE",
            dest="db_modules",
            help="Tortoise ORM modules to build models from (REQUIRED) (multi-allowed)",
        )
        group.add_argument(
            "--db-url",
            action="store",
            default="",
            metavar="URI",
            dest="db_url",
            help="Tortoise ORM test DB-URL",
        )

    def handleArgs(self, event: Event) -> None:
        """Get our options in order command line, config file, hard coded."""
        self.db_url = event.args.db_url or self.db_url
        self.db_modules = event.args.db_modules or self.db_modules

    def startTestRun(self, event: Event) -> None:
        initializer(self.db_modules, db_url=self.db_url)

    def stopTestRun(self, event: Event) -> None:
        finalizer()
