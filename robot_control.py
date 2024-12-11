import threading
import logging
import time
from unitree_sdk2py.go2.sport.sport_client import SportClient

logger = logging.getLogger(__name__)

class RobotControl:
    def __init__(self, network_interface='eth0'):
        self.network_interface = network_interface
        self.client = None
        self.running = False
        self.move_thread = None
        self.x_speed = 0
        self.y_speed = 0
        self.yaw_speed = 0
        self.lock = threading.Lock()

    def initialize(self):
        try:
            logger.info("Initializing robot control...")
            self.client = SportClient()
            self.client.SetTimeout(10.0)
            self.client.Init()
            self.running = True
            # Start the movement thread
            self.move_thread = threading.Thread(target=self._movement_loop)
            self.move_thread.daemon = True
            self.move_thread.start()
            return True
        except Exception as e:
            logger.error(f"Robot control initialization error: {str(e)}")
            return False

    def cleanup(self):
        self.running = False
        if self.move_thread:
            self.move_thread.join()

    def _movement_loop(self):
        while self.running:
            with self.lock:
                x_speed = self.x_speed
                y_speed = self.y_speed
                yaw_speed = self.yaw_speed
            try:
                # Always send movement commands
                if y_speed != 0 or x_speed != 0 or yaw_speed != 0:
                    self.client.Move(y_speed, x_speed, yaw_speed)
            except Exception as e:
                logger.error(f"Error sending Move command: {e}")
            time.sleep(0.02)  # Sleep for 20ms

    def set_speeds(self, x_speed, y_speed, yaw_speed):
        with self.lock:
            self.x_speed = x_speed
            self.y_speed = y_speed
            self.yaw_speed = yaw_speed

    def stand_up(self):
        with self.lock:
            self.x_speed = 0
            self.y_speed = 0
            self.yaw_speed = 0
        if self.client:
            self.client.StandUp()

    def stand_down(self):
        with self.lock:
            self.x_speed = 0
            self.y_speed = 0
            self.yaw_speed = 0
        if self.client:
            self.client.StandDown()

    def stop_move(self):
        with self.lock:
            self.x_speed = 0
            self.y_speed = 0
            self.yaw_speed = 0
        if self.client:
            self.client.StopMove()

    def balance_stand(self):
        if self.client:
            self.client.BalanceStand()

    def recovery_stand(self):
        if self.client:
            self.client.RecoveryStand()

    def switch_gait(self, gait_type):
        if self.client:
            self.client.SwitchGait(gait_type)