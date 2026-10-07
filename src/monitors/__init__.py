"""Named source adapters for the autonomous poll monitor."""
from .cis_monitor import CISMonitor
from .electomania_monitor import ElectomaniaMonitor
from .dato_electoral_monitor import DatoElectoralMonitor
from .twitter_monitor import TwitterMonitor
__all__ = ["CISMonitor", "ElectomaniaMonitor", "DatoElectoralMonitor", "TwitterMonitor"]
