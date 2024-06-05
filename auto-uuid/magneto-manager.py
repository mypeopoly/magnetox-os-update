from flask import Flask, request, jsonify
import os
import re
import socket
import subprocess
import shutil
import glob
import serial
import serial.tools.list_ports

CONFIG_PATH = "/home/pi/printer_data/config/magneto_device.cfg"
BACKUP_PATH = "/home/pi/printer_data/config/magneto_device.cfg.bak"
VERSION_STR = "magneto-x-mainsailOS-2024-5-1-v1.1.3-mag-x"

app = Flask(__name__)
serial_connection = None


def connect_to_serial():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # print(port.description)
        if "USB Serial" in port.description:
            try:
                return serial.Serial(port.device, 115200)
            except Exception as e:
                print("Connect failed:")
    return None


@app.route("/get_os_version", methods=["GET"])
def get_os_version():
    return jsonify({"version": VERSION_STR})


@app.route("/get_git_version", methods=["GET"])
def get_git_version():
    subprocess.run(
        [
            "git",
            "config",
            "--global",
            "--add",
            "safe.directory",
            "/home/pi/magnetox-os-update",
        ]
    )
    version_from_git_branch = subprocess.run(
        [
            "git",
            "-C",
            "/home/pi/magnetox-os-update/",
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    version_from_git_commit = subprocess.run(
        ["git", "-C", "/home/pi/magnetox-os-update/", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return jsonify(
        {
            "git_branch": version_from_git_branch.stdout.replace("\n", ""),
            "git_commit": version_from_git_commit.stdout.replace("\n", ""),
        }
    )


@app.route("/connect_lm", methods=["GET"])
def connect_esplm():
    global serial_connection
    serial_connection = connect_to_serial()
    if serial_connection is None:
        return jsonify({"error": "No device foune"})
    else:
        print(f"Connectd {serial_connection.port}")
        return jsonify({"connected": serial_connection.port})


@app.route("/disconnect_lm", methods=["GET"])
def disconnect_serial():
    global serial_connection
    if serial_connection and serial_connection.is_open:
        serial_connection.close()
        print("Serial connection closed.")
        return jsonify({"info": "Serial connection closed"})
    else:
        print("No open serial connection to close.")
        return jsonify({"info": "No open serial connection to close"})


@app.route("/motor_control", methods=["GET"])
def linear_motor_debug():
    try:
        result = subprocess.run(
            "/home/pi/auto-uuid/mag_motor_control.sh",
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"mag motor:\n{result.stdout}")
        print(f"mag motor error\n{result.stderr}")
    except subprocess.CalledProcessError as e:
        print(f"mag motor script error{e}")
    except Exception as e:
        print(f"mag motor execut error:{e}")


@app.route("/send_command", methods=["GET"])
def send_command():
    global serial_connection
    if not serial_connection:
        return jsonify({"error": "Serial port no connected"})

    command = request.args.get("command") + "\n"

    if command:
        try:
            serial_connection.write(command.encode())
            return jsonify({"suc": "Send success"})
        except Exception as e:
            return jsonify({"error": "Send failed"})
    else:
        return jsonify({"error": "Invalid command"})


@app.route("/auto_resize_filesystem", methods=["GET"])
def auto_resize_filesystem():
    try:
        output = run_command("systemctl start orangepi-resize-filesystem.service")
        print("resize filesystem")
        return jsonify({"success": output})
    except subprocess.CalledProcessError as e:
        return jsonify({"success": f"Error occurred while resize filesystem: {e}"})


def run_command(command):
    try:
        output = subprocess.check_output(
            command, shell=True, stderr=subprocess.STDOUT
        ).decode("utf-8")
        return output
    except subprocess.CalledProcessError as e:
        return e.output.decode("utf-8")


def extract_uuids(output):
    uuids = re.findall(r"canbus_uuid=(\w+)", output)
    return uuids


def backup_config_file(filename):
    backup_filename = filename + ".backup"
    shutil.copy2(filename, backup_filename)


def modify_config_file(filename, uuid):
    with open(filename, "r") as file:
        lines = file.readlines()

    for index, line in enumerate(lines):
        if "canbus_uuid:" in line:
            lines[index] = f"canbus_uuid: {uuid}\n"
            break

    with open(filename, "w") as file:
        file.writelines(lines)
        file.flush()
        os.fsync(file.fileno())

    ## mcu uuid get


def get_serial_devices():
    devices = glob.glob("/dev/serial/by-id/*")
    return devices


def backup_config():
    shutil.copy2(CONFIG_PATH, BACKUP_PATH)


def update_config_file(device):
    if not device:
        return

    with open(CONFIG_PATH, "r") as file:
        content = file.readlines()

    mcu_section_found = False
    for index, line in enumerate(content):
        if line.strip() == "[mcu]":
            mcu_section_found = True

            while "serial:" not in content[index] and content[index].strip() != "":
                index += 1
            if "serial:" in content[index]:
                content[index] = "serial: {}\n".format(device)
                break

    if not mcu_section_found:
        content.append("\n[mcu]\n")
        content.append("serial: {}\n".format(device))

    with open(CONFIG_PATH, "w") as file:
        file.writelines(content)
        file.flush()
        os.fsync(file.fileno())


@app.route("/get-ip", methods=["GET"])
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 使用一个不存在的地址，目的是为了初始化一个连接，以获取正确的IP
        s.connect(("10.255.255.255", 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    return jsonify({"ip": IP})


@app.route("/get-mcu-uuid", methods=["GET"])
def get_mcu_uuid():
    if not os.path.exists(CONFIG_PATH):
        print("Error: Config file not found at", CONFIG_PATH)
        return jsonify({"error": "Config file not found"})

    devices = get_serial_devices()
    if len(devices) > 0:
        for device in devices:
            if device.startswith("/dev/serial/by-id/usb-Klipper"):
                return jsonify({"mcu-uuid": device})


@app.route("/set-mcu-uuid", methods=["GET"])
def set_mcu_uuid():
    if not os.path.exists(CONFIG_PATH):
        print("Error: Config file not found at", CONFIG_PATH)
        return jsonify({"error": "Config file not found"})

    devices = get_serial_devices()
    if len(devices) > 0:
        for device in devices:
            if device.startswith("/dev/serial/by-id/usb-Klipper"):
                backup_config()
                update_config_file(device)
                return jsonify({"mcu-uuid-success": device})

    else:
        return jsonify({"error": "No MCU uuid found"})


@app.route("/set-can-uuid", methods=["GET"])
def set_can_uuid():
    config_path = "/home/pi/printer_data/config/magneto_device.cfg"

    # 检查文件是否存在
    if not os.path.exists(config_path):
        return jsonify({"error": f"{config_path} not found!"})

    # 执行备份
    backup_config_file(config_path)

    command = (
        "/home/pi/klippy-env/bin/python /home/pi/klipper/scripts/canbus_query.py can0"
    )
    output = run_command(command)
    uuids = extract_uuids(output)

    # 判断uuids的数量并取适当的值
    if len(uuids) == 2:
        uuid_to_use = uuids[-1]
        modify_config_file(config_path, uuid_to_use)
        return jsonify({"suc": "set canbus uuid successful"})
    else:
        return jsonify({"error": f"only {len(uuid_to_use)}  found!"})


@app.route("/get-can-uuid", methods=["GET"])
def get_can_uuid():
    command = (
        "/home/pi/klippy-env/bin/python /home/pi/klipper/scripts/canbus_query.py can0"
    )
    output = run_command(command)
    uuids = extract_uuids(output)

    return jsonify({"can-uuids": uuids})


if __name__ == "__main__":
    serial_connection = connect_to_serial()
    if serial_connection is None:
        print("No device found!")
    else:
        print(f"Connected {serial_connection.port}")
    app.run(host="0.0.0.0", port=8880)