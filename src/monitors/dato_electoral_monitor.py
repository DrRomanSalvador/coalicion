from ..poll_monitor import SourceMonitor, parse_dato_electoral
class DatoElectoralMonitor(SourceMonitor):
    def parse(self, body: bytes):
        return parse_dato_electoral(body, self.source), []
