from typing import Dict, Any
from .mocap_base import MocapBase
from .vicon_stream import ViconStream
from .qtm_mocap import QTMStream

def create_mocap_system(config: Dict[str, Any]) -> MocapBase:
    """Create a mocap system based on configuration.
    
    Args:
        config: Configuration dictionary containing mocap settings
        
    Returns:
        An instance of a MocapBase implementation
        
    Raises:
        ValueError: If the specified mocap system is not supported
    """
    system = config.get("mocap", {}).get("system", "qtm")
    
    if system == "vicon":
        vicon_config = config.get("mocap", {}).get("vicon", {})
        return ViconStream(
            vicon_host=vicon_config.get("host", "192.168.0.100"),
            udp_ip=vicon_config.get("udp_ip", "192.168.0.100"),
            udp_port=vicon_config.get("udp_port", 51001)
        )
    elif system == "qtm":
        qtm_config = config.get("mocap", {}).get("qtm", {})
        return QTMStream(
            qtm_ip=qtm_config.get("host", "192.168.100.1")
        )
    else:
        raise ValueError(f"Unsupported mocap system: {system}")
