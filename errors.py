class ParseError(Exception):
    def __init__(self, line_number: int | None, message: str) -> None:
        if line_number is None:
            super().__init__(message)
        else:
            super().__init__(f"line {line_number}: {message}")


class SimulationError(Exception):
    pass
