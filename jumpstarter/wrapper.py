from jumpstarter.common.utils import env
from jumpstarter_driver_network.adapters import TcpPortforwardAdapter
import time
import sys
import os
import subprocess


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

            # FIXME
            os.environ["JETSON_USERNAME"] = "admin"
            os.environ["JETSON_PASSWORD"] = "password"

            subprocess.run(sys.argv[1:])
