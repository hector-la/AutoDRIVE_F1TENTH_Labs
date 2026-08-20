#!/usr/bin/env python3
"""
Keyboard teleop for the AutoDRIVE F1TENTH vehicle, mixing two control styles
on purpose:

- Throttle (W/S) is a LATCH: press once, it holds that value until you press
  another throttle key or X. This is deliberate — a terminal can't reliably
  detect two keys held down at the same time (no true simultaneous key
  events over a serial input stream), so if throttle also required holding
  W, you couldn't free a finger to steer with A/D while moving. Latching
  throttle solves that: go forward, then steer freely.
- Steering (A/D) is HOLD-TO-CENTER: holding it applies a fixed turn, letting
  go straightens the wheel back to 0 — this one you naturally do one at a
  time anyway (you're not holding A and D together), so hold-to-release
  behavior works fine and gives more natural cornering than a steering latch
  would (you'd have to remember to re-center it every turn).

Supports arrow keys (preferred) and WASD.

How "hold" is detected for steering, without a GUI:
A raw terminal never reports key-release, only key-press. What it does give
us for free is the OS's keyboard auto-repeat: while a key stays physically
held, the terminal keeps re-sending it every ~30-50ms. So we track the last
time the steering key repeated, and if nothing arrives for WATCHDOG_TIMEOUT
seconds, we treat it as released and zero the steering. If your keyboard's
repeat rate is unusually slow, raise WATCHDOG_TIMEOUT.
"""

import rclpy
from rclpy.qos import QoSProfile
from std_msgs.msg import Float32

import os
import select
import sys
import time

if os.name == 'nt':
    import msvcrt
else:
    import termios
    import tty

################################################################################

# Parameters
DRIVE_VALUE = 0.5        # throttle_command sent while accelerate/reverse is held, in [-1, 1]
STEER_VALUE = 0.5        # steering_command sent while a turn key is held, in [-1, 1]
WATCHDOG_TIMEOUT = 0.15  # seconds without a key repeat before treating it as "released"
POLL_TIMEOUT = 0.05      # how often we poll stdin / check the watchdog

INFO = """
-------------------------------------------------
AutoDRIVE - F1TENTH Teleop
-------------------------------------------------

           UP / W
  LEFT / A          RIGHT / D
          DOWN / S

W / S   : go forward / reverse (latches, stays until changed)
A / D   : steer left / right (hold to turn, release to straighten)
X       : stop and straighten
CTRL+C  : quit

NOTE: this terminal window must stay focused.
-------------------------------------------------
"""

################################################################################

def get_key(settings, timeout=POLL_TIMEOUT):
    """Read one keypress. Arrow keys arrive as multi-byte escape sequences
    (ESC [ A/B/C/D on POSIX) and are resolved to 'UP'/'DOWN'/'LEFT'/'RIGHT'."""
    if os.name == 'nt':
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            if ch in (b'\x00', b'\xe0'):  # arrow-key prefix on Windows
                ch2 = msvcrt.getch()
                return {b'H': 'UP', b'P': 'DOWN', b'K': 'LEFT', b'M': 'RIGHT'}.get(ch2, '')
            return ch.decode('utf-8', errors='ignore')
        return ''

    tty.setraw(sys.stdin.fileno())
    key = ''
    rlist, _, _ = select.select([sys.stdin], [], [], timeout)
    if rlist:
        ch = sys.stdin.read(1)
        if ch == '\x1b':  # start of an escape sequence
            rlist2, _, _ = select.select([sys.stdin], [], [], timeout)
            if rlist2:
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    key = {'A': 'UP', 'B': 'DOWN', 'C': 'RIGHT', 'D': 'LEFT'}.get(ch3, '')
            if not key:
                key = '\x1b'  # bare ESC (used to quit cleanly if needed)
        else:
            key = ch
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key


def constrain(value, low, high):
    return max(low, min(high, value))

################################################################################

def main():
    settings = None if os.name == 'nt' else termios.tcgetattr(sys.stdin)

    rclpy.init()
    qos = QoSProfile(depth=1)
    node = rclpy.create_node('teleop_hold')
    pub_throttle_command = node.create_publisher(Float32, '/autodrive/f1tenth_1/throttle_command', qos)
    pub_steering_command = node.create_publisher(Float32, '/autodrive/f1tenth_1/steering_command', qos)

    throttle_msg = Float32()
    steering_msg = Float32()
    throttle = 0.0
    steering = 0.0
    last_steering_key_time = 0.0

    try:
        print(INFO)
        while True:
            key = get_key(settings)
            now = time.monotonic()

            if key in ('w', 'W', 'UP'):
                throttle = DRIVE_VALUE       # latches: stays until S or X
            elif key in ('s', 'S', 'DOWN'):
                throttle = -DRIVE_VALUE      # latches: stays until W or X
            elif key in ('a', 'A', 'LEFT'):
                steering = STEER_VALUE
                last_steering_key_time = now
            elif key in ('d', 'D', 'RIGHT'):
                steering = -STEER_VALUE
                last_steering_key_time = now
            elif key in ('x', 'X'):
                throttle = 0.0
                steering = 0.0
            elif key == '\x03':  # CTRL+C
                break

            # Steering only: no repeat of the held key within WATCHDOG_TIMEOUT -> released
            if steering != 0.0 and (now - last_steering_key_time) > WATCHDOG_TIMEOUT:
                steering = 0.0

            throttle_msg.data = float(constrain(throttle, -1.0, 1.0))
            steering_msg.data = float(constrain(steering, -1.0, 1.0))
            pub_throttle_command.publish(throttle_msg)
            pub_steering_command.publish(steering_msg)

    finally:
        # Always leave the vehicle stopped on exit
        throttle_msg.data = 0.0
        steering_msg.data = 0.0
        pub_throttle_command.publish(throttle_msg)
        pub_steering_command.publish(steering_msg)
        if os.name != 'nt':
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        rclpy.shutdown()

################################################################################

if __name__ == '__main__':
    main()
