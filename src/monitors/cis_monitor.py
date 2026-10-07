from ..poll_monitor import SourceMonitor, parse_rss_metadata
class CISMonitor(SourceMonitor):
    """CIS RSS/discovery adapter."""
    def parse(self, body: bytes):
        return [], parse_rss_metadata(body, self.source)
