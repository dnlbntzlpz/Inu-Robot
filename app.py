from flask import Flask, render_template, redirect, url_for
from flask_socketio import SocketIO
import logging
import sys
import threading
from models import db
from robot_control import RobotControl
from camera_stream import camera_config
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
    # Test route without authentication
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

    camera_config.set_socketio(socketio)
    if camera_config.initialize():
        thread = threading.Thread(target=camera_config.process_frames)
        thread.daemon = True
        thread.start()
        logger.info("Camera streaming started successfully.")
    else:
        logger.error("Failed to initialize robot camera.")

    robot_control = RobotControl(network_interface='eth0')
    if robot_control.initialize():
        logger.info("Robot control initialized successfully.")
    else:
        logger.error("Failed to initialize robot control.")

    app.debug = True
    try:
        socketio.run(app, host='0.0.0.0', port=8066, allow_unsafe_werkzeug=True)
    finally:
        if camera_config:
            camera_config.cleanup()
        if robot_control:
            robot_control.cleanup()
