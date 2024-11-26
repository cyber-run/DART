import sys
from pathlib import Path
import time
import logging

# Add src to path
src_path = Path(__file__).parent.parent
sys.path.append(str(src_path))

from hardware.motion.theia_controller import TheiaController
from core.config_manager import ConfigManager

logging.basicConfig(level=logging.INFO)

def test_position_persistence():
    """Test whether lens positions are maintained between connections"""
    config = ConfigManager()
    theia_port = config.config["devices"]["theia_port"]
    
    # First connection
    logging.info("First connection - Moving to test positions")
    theia1 = TheiaController(theia_port)
    theia1.connect()
    theia1.initialise()
    
    # Move to test positions
    zoom_steps = 10000
    focus_steps = 20000
    
    logging.info(f"Moving zoom to {zoom_steps} steps")
    theia1.move_axis("A", zoom_steps)
    time.sleep(1)
    
    logging.info(f"Moving focus to {focus_steps} steps")
    theia1.move_axis("B", focus_steps)
    time.sleep(1)
    
    # Disconnect
    logging.info("Disconnecting first instance")
    theia1.disconnect()
    time.sleep(2)
    
    # Second connection
    logging.info("Second connection - Testing relative movements")
    theia2 = TheiaController(theia_port)
    theia2.connect()
    theia2.initialise()
    
    # Test small movements and observe behavior
    test_steps = 1000
    
    logging.info(f"Moving zoom by {test_steps} steps")
    theia2.move_axis("A", test_steps)
    time.sleep(1)
    
    logging.info(f"Moving focus by {test_steps} steps")
    theia2.move_axis("B", test_steps)
    time.sleep(1)
    
    # Try to return to "zero"
    logging.info("Attempting to return to zero")
    theia2.move_axis("A", -zoom_steps - test_steps)
    theia2.move_axis("B", -focus_steps - test_steps)
    
    theia2.disconnect()

if __name__ == "__main__":
    test_position_persistence() 