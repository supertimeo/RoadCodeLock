class ScraperError(Exception):
    pass


class NavigationError(ScraperError):
    pass


class ElementNotFoundError(NavigationError):
    pass


class ParsingError(ScraperError):
    pass


class FormNotFoundError(ParsingError):
    pass


class ExplanationsNotFoundError(ParsingError):
    pass


class MediaExtractionError(ScraperError):
    pass


class MediaSaveError(ScraperError):
    pass