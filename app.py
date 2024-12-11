from flask import Flask, render_template, redirect, url_for
from flask_socketio import SocketIO
import cv2
import base64
import threading
import time
import logging
from models import db
from robot_control import RobotControl
from camera_stream import camera_config  # Only import Unitree Go2 camera config
from unitree_sdk2py.core.channel import ChannelFactoryInitialize

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

robot_control = None


@app.route('/')
def index():
    return redirect(url_for('control'))


@app.route('/control')
def control():
    return render_template('control.html')


@socketio.on('control_command')
def handle_control_command(data):
    global robot_control
    if robot_control is None:
        logger.warning("Robot control not initialized yet")
        return

    command = data.get('command')
    if command == 'move':
        y_speed = data.get('y_speed', 0)
        x_speed = data.get('x_speed', 0)
        yaw_speed = data.get('yaw_speed', 0)
        robot_control.set_speeds(x_speed, y_speed, yaw_speed)
    else:
        robot_control.set_speeds(0, 0, 0)
        if command == 'stand_up':
            robot_control.stand_up()
            robot_control.balance_stand()
        elif command == 'stand_down':
            robot_control.stand_down()
        elif command == 'stop_move':
            robot_control.stop_move()
        elif command == 'balance_stand':
            robot_control.balance_stand()
        elif command == 'recovery_stand':
            robot_control.recovery_stand()
        elif command == 'switch_gait':
            gait_type = data.get('gait_type', 0)
            robot_control.switch_gait(gait_type)
        elif command == 'sit_down':
            robot_control.sit()
        else:
            logger.warning(f"Unknown command: {command}")


def init_usb_camera(camera_index=0, width=320, height=240, fps=15):
    """
    Initialize and stream USB camera frames.
    """
    try:
        # Release any previously opened camera
        existing_capture = globals().get("usb_capture")
        if existing_capture and existing_capture.isOpened():
            existing_capture.release()
            logger.info("Released previously opened USB camera.")

        capture = cv2.VideoCapture(camera_index)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        capture.set(cv2.CAP_PROP_FPS, fps)

        if not capture.isOpened():
            logger.error(f"Failed to open USB camera at index {camera_index}.")
            return None

        logger.info(f"USB camera at index {camera_index} initialized successfully.")

        def process_usb_frames():
            while True:
                ret, frame = capture.read()
                if not ret:
                    logger.error("Failed to capture frame from USB camera.")
                    time.sleep(0.1)
                    continue

                # Compress and emit frame
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 50]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)
                frame_data = base64.b64encode(buffer).decode('utf-8')
                socketio.emit('usb_frame', {'data': frame_data})
                time.sleep(1 / fps)

        thread = threading.Thread(target=process_usb_frames)
        thread.daemon = True
        thread.start()
        logger.info("Started USB camera frame streaming.")
        return capture
    except Exception as e:
        logger.error(f"Error initializing USB camera: {str(e)}")
        return None


def init_db():
    with app.app_context():
        db.create_all()


if __name__ == '__main__':
    init_db()

    try:
        ChannelFactoryInitialize(0, 'eth0')
        logger.info("ChannelFactory initialized successfully.")
    except Exception as e:
        logger.error(f"ChannelFactory initialization error: {str(e)}")
        sys.exit(1)

    # Initialize Unitree Go2 camera
    camera_config.set_socketio(socketio)
    if camera_config.initialize():
        thread = threading.Thread(target=camera_config.process_frames)
        thread.daemon = True
        thread.start()
        logger.info("Unitree Go2 camera streaming started successfully.")
    else:
        logger.error("Failed to initialize Unitree Go2 camera.")

    # Initialize USB camera
    usb_capture = init_usb_camera(camera_index=0)
    if usb_capture is None:
        logger.error("USB camera initialization failed.")

    # Initialize robot control
    robot_control = RobotControl(network_interface='eth0')
    if robot_control.initialize():
        logger.info("Robot control initialized successfully.")
    else:
        logger.error("Failed to initialize robot control.")

    # Start Flask application with Socket.IO
    app.debug = True
    try:
        socketio.run(app, host='0.0.0.0', port=8066, allow_unsafe_werkzeug=True, use_reloader=False)
    finally:
        # Cleanup resources
        if camera_config:
            camera_config.cleanup()
        if usb_capture:
            usb_capture.release()
        if robot_control:
            robot_control.cleanup()
