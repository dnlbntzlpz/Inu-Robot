import cv2
import numpy as np
import base64
import time
import logging
from unitree_sdk2py.go2.video.video_client import VideoClient

logger = logging.getLogger(__name__)

class RobotCameraConfig:
    def __init__(self, width=320, height=240):  # Reduced resolution
        self.width = width
        self.height = height
        self.client = None
        self.running = False
        self.target_fps = 15  # Reduced FPS
        self.frame_interval = 1.0 / self.target_fps
        self.jpeg_quality = 50  # Reduced quality
        self.skip_frames = 2  # Process every nth frame
        self.last_frame_time = 0
        self.frame_count = 0
        self.socketio = None  # Add socketio as instance variable

    def set_socketio(self, socketio):
        self.socketio = socketio

    def initialize(self):
        try:
            logger.info("Initializing robot camera...")
            self.client = VideoClient()
            self.client.SetTimeout(3.0)
            self.client.Init()

            code, _ = self.client.GetImageSample()
            if code != 0:
                logger.error(f"Failed to get image from robot camera. Error code: {code}")
                return False

            self.running = True
            return True
        except Exception as e:
            logger.error(f"Robot camera initialization error: {str(e)}")
            return False

    def cleanup(self):
        self.running = False
        if self.client is not None:
            pass

    def process_frames(self):
        """Optimized frame capture and processing"""
        skip_count = 0

        while self.running:
            current_time = time.time()
            elapsed = current_time - self.last_frame_time

            # Skip frames if we're falling behind
            if elapsed < self.frame_interval:
                time.sleep(0.001)  # Short sleep to prevent CPU hogging
                continue

            try:
                skip_count += 1
                if skip_count < self.skip_frames:
                    continue
                skip_count = 0

                # Get frame from robot camera
                code, data = self.client.GetImageSample()

                if code == 0 and self.socketio is not None:  # Check if socketio is set
                    # Convert to numpy array and decode
                    image_data = np.frombuffer(bytes(data), dtype=np.uint8)
                    frame = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

                    # Resize frame to reduce processing load
                    frame = cv2.resize(frame, (self.width, self.height))

                    # Compress frame with lower quality
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
                    _, buffer = cv2.imencode('.jpg', frame, encode_param)

                    # Emit frame
                    frame_data = base64.b64encode(buffer).decode('utf-8')
                    self.socketio.emit('frame', {'data': frame_data})

                    self.frame_count += 1
                    if self.frame_count % self.target_fps == 0:
                        actual_fps = self.target_fps / (current_time - self.last_frame_time)
                        logger.debug(f"Streaming at {actual_fps:.1f} FPS")
                        self.frame_count = 0

                    self.last_frame_time = current_time
                else:
                    logger.error(f"Failed to get image from robot camera. Error code: {code}")
                    time.sleep(0.1)

            except Exception as e:
                logger.error(f"Frame processing error: {str(e)}")
                time.sleep(0.1)

# Create a global camera_config instance
camera_config = RobotCameraConfig()