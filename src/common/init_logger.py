import sys
from enum import StrEnum
from typing import TYPE_CHECKING

from loguru import logger

from common.paths import log_folder_path

if TYPE_CHECKING:
    from loguru import Record

class LoggingLevels(StrEnum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def log_patcher(record: Record):
    """Enrichit un enregistrement de log avec des informations de localisation et de thread.
    Cette fonction prépare les champs supplémentaires utilisés par le formatteur de logs.

    Args:
        record (Record): L'enregistrement de log à modifier, contenant les informations
            de contexte et les champs extra.
    """
    class_name = record["extra"].get("class_name")
    record["extra"]["location"] = f"{record['file'].name}{f":{class_name}" if class_name is not None else ""}{f":{record['function']}" if record['function'] != "<module>" else ""}:{record['line']}"
    record["extra"]["thread_info"] = f"{record["thread"].name} ({record["thread"].id})"


def log_format(_record: Record) -> str:
    """Construit une chaîne de formatage pour les messages de log enrichis.
    Cette fonction définit la présentation des informations de temps, niveau, localisation, thread et message.

    Args:
        _record (Record): L'enregistrement de log à formatter, utilisé pour alimenter les champs du gabarit.

    Returns:
        str: Le gabarit de formatage à utiliser par Loguru pour rendre les messages de log.
    """
    return (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "<level>{level: <8}</level> | "
        "{extra[location]: <50} | "
        "{extra[thread_info]: <20} - "
        "{message}\n"
        "{exception}"
    )


def init_logger(app: str):
    """Initialise et configure le système de journalisation de l'application crawler TUI.
    Cette fonction prépare les fichiers de logs, les niveaux personnalisés et le sink Textual pour l'affichage dans l'interface.
    """

    # création du logger
    logger.remove()

    logger.configure(patcher=log_patcher)

    logger.add(sys.stdout, level=LoggingLevels.TRACE, format=log_format)
    logger.add(log_folder_path / app / "latest" / "latest.log", rotation="1 MB", retention="7 days", compression="zip", level=LoggingLevels.INFO,
               format=log_format)
    logger.add(log_folder_path / app / "error" / "error.log", rotation="200 MB", retention="7 days", compression="zip", level=LoggingLevels.ERROR,
               format=log_format, backtrace=True, diagnose=True)
    logger.add(log_folder_path / app / "trace" / "trace.log", rotation="10 GB", retention="7 days", compression="zip", level=LoggingLevels.TRACE,
               format=log_format)

    logger.info("Logger initialized")