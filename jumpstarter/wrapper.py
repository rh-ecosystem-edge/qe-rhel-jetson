from jumpstarter.common.utils import env
from jumpstarter_driver_network.adapters import TcpPortforwardAdapter
import time
import sys
import os
import subprocess
import importlib
from pathlib import Path


USERNAME = os.environ.get("JETSON_USERNAME")
PASSWORD = os.environ.get("JETSON_PASSWORD")

if USERNAME is None or PASSWORD is None:
    raise ValueError(
        "JETSON_USERNAME and JETSON_PASSWORD must be set when running tests over jumpstarter"
    )

with env() as client:
    with client.log_stream():
        client.storage.dut()
        print("Storage connected to DUT")
        client.power.cycle()
        print("DUT powered on")

        with client.serial.pexpect() as p:
            p.logfile = sys.stdout.buffer
            p.expect_exact("login:", timeout=600)
            print("Successfully showing login prompt via console")

        # Wait for SSH service to be ready
        print("Waiting for SSH service to start...")
        time.sleep(10)

        with TcpPortforwardAdapter(client=client.ssh.tcp) as addr:
            os.environ["JETSON_HOST"] = addr[0]
            os.environ["JETSON_PORT"] = str(addr[1])

            project_root = Path(__file__).parent.parent
            sys.path.insert(0, str(project_root))
            ssh_client_path = project_root / "infra-tests" / "ssh_client.py"
            spec = importlib.util.spec_from_file_location("ssh_client", ssh_client_path)
            ssh_client_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ssh_client_module)
            SSHConnection = ssh_client_module.SSHConnection

            with SSHConnection(
                addr[0],
                USERNAME,
                PASSWORD,
                addr[1],
            ) as ssh:
                ssh.sudo("/usr/libexec/bootc-generic-growpart")

            subprocess.run(sys.argv[1:])
