"""
YOLO UDP Receiver - Grasshopper Component
Receives YOLOv8 pose detection data via UDP and outputs keypoint positions

    Args:
        port: UDP port number (default: 9999)
        target_joint: Target joint name (e.g., 'left_wrist', 'nose', 'right_shoulder')

    Returns:
        point: Target joint position as Point3d
        x: X coordinate
        y: Y coordinate
        z: Z coordinate
        all_points: All detected keypoints as Point3d list
        joint_names: List of all detected joint names
        message: Status message
        debug: Debug information
"""

from ghpythonlib.componentbase import executingcomponent as component

import clr
clr.AddReference("System")
clr.AddReference("RhinoCommon")

from System.Net import IPEndPoint, IPAddress
from System.Net.Sockets import Socket, AddressFamily, SocketType, ProtocolType
from System.Net.Sockets import SocketOptionLevel, SocketOptionName
from System.Text import Encoding
import Rhino.Geometry as rg
import System


class YOLOUDPReceiver(component):
    # Class variables to maintain state across calls
    _udp_socket = None
    _keypoints = {}

    @staticmethod
    def parse_json(text):
        """Simple JSON parser without external dependencies"""
        result = {}
        text = text.strip('{}').replace('"', '').replace(' ', '')
        for pair in text.split(','):
            if ':' not in pair:
                continue
            k, v = pair.split(':', 1)
            try:
                result[k] = float(v) if '.' in v else int(v)
            except:
                result[k] = v
        return result

    def RunScript(self, port, target_joint):
        ghenv.Component.Message = 'v{{version}}'

        # Initialize outputs
        x = 0.0
        y = 0.0
        z = 0.0
        point = rg.Point3d(0.0, 0.0, 0.0)
        all_points = []
        joint_names = []
        message = "Initializing..."
        debug_lines = []

        try:
            # Process inputs
            port_num = int(port) if port else 9999
            target = str(target_joint).strip() if target_joint else "left_wrist"

            debug_lines.append("Port: {}".format(port_num))
            debug_lines.append("Target: '{}'".format(target))

            # Setup socket
            if YOLOUDPReceiver._udp_socket is None:
                YOLOUDPReceiver._udp_socket = Socket(
                    AddressFamily.InterNetwork,
                    SocketType.Dgram,
                    ProtocolType.Udp
                )
                YOLOUDPReceiver._udp_socket.Blocking = False
                YOLOUDPReceiver._udp_socket.ReceiveTimeout = 10
                YOLOUDPReceiver._udp_socket.SetSocketOption(
                    SocketOptionLevel.Socket,
                    SocketOptionName.ReuseAddress,
                    True
                )
                YOLOUDPReceiver._udp_socket.Bind(
                    IPEndPoint(IPAddress.Parse("127.0.0.1"), port_num)
                )
                debug_lines.append("Socket created")

            # Receive data
            buffer = System.Array.CreateInstance(System.Byte, 8192)
            received = 0

            for i in range(50):
                try:
                    n = YOLOUDPReceiver._udp_socket.Receive(buffer)
                    if n > 0:
                        received += 1
                        text = Encoding.UTF8.GetString(buffer, 0, n)
                        data = self.parse_json(text)

                        if 'keypoint' in data.get('type', ''):
                            name = data.get('name', '')
                            if name:
                                YOLOUDPReceiver._keypoints[name] = {
                                    'x': float(data.get('x', 0)),
                                    'y': float(data.get('y', 0)),
                                    'confidence': float(data.get('confidence', 1.0))
                                }
                except System.Net.Sockets.SocketException:
                    break
                except:
                    break

            debug_lines.append("Received {} packets".format(received))
            debug_lines.append("Keypoints: {}".format(len(YOLOUDPReceiver._keypoints)))

            # Process target joint
            if target in YOLOUDPReceiver._keypoints:
                kp = YOLOUDPReceiver._keypoints[target]

                # Scale coordinates (0-1 normalized to 0-100)
                x = float(kp['x']) * 100.0
                y = float(kp['y']) * 100.0
                z = 0.0

                # Create Point3d
                point = rg.Point3d(x, y, z)

                debug_lines.append("✓ Found '{}'".format(target))
                debug_lines.append("Raw: ({:.4f}, {:.4f})".format(kp['x'], kp['y']))
                debug_lines.append("Scaled: ({:.2f}, {:.2f}, {:.2f})".format(x, y, z))

                message = "OK: {} ({} pts)".format(target, len(YOLOUDPReceiver._keypoints))
            else:
                point = rg.Point3d(0.0, 0.0, 0.0)

                if YOLOUDPReceiver._keypoints:
                    available = ', '.join(list(YOLOUDPReceiver._keypoints.keys())[:5])
                    message = "✗ No '{}' (available: {})".format(target, available)
                    debug_lines.append("✗ Target '{}' not found".format(target))
                    debug_lines.append("Available: {}".format(', '.join(YOLOUDPReceiver._keypoints.keys())))
                else:
                    message = "✗ No data"
                    debug_lines.append("✗ No keypoints data")

            # Process all joints
            all_points = []
            joint_names = []
            for name in sorted(YOLOUDPReceiver._keypoints.keys()):
                kp = YOLOUDPReceiver._keypoints[name]
                pt = rg.Point3d(float(kp['x']) * 100.0, float(kp['y']) * 100.0, 0.0)
                all_points.append(pt)
                joint_names.append(name)

            debug_lines.append("all_points: {}".format(len(all_points)))

        except Exception as e:
            message = "ERROR: {}".format(str(e)[:50])
            debug_lines = ["Exception: {}".format(str(e))]
            x = 0.0
            y = 0.0
            z = 0.0
            point = rg.Point3d(0.0, 0.0, 0.0)

        debug = "\n".join(debug_lines)

        return (point, x, y, z, all_points, joint_names, message, debug)
