from jumpstarter.common.utils import env
from jumpstarter_driver_network.adapters import TcpPortforwardAdapter
import time
import sys
import os
import subprocess
from pathlib import Path


USERNAME = os.environ.get("JETSON_USERNAME")
PASSWORD = os.environ.get("JETSON_PASSWORD")
KEY_PATH = os.environ.get("JETSON_KEY_PATH")

if USERNAME is None:
    raise ValueError("JETSON_USERNAME must be set when running tests over jumpstarter")
if PASSWORD is None and KEY_PATH is None:
    raise ValueError(
        "JETSON_PASSWORD or JETSON_KEY_PATH must be set when running tests over jumpstarter"
    )

# Resolve key path
key_filename = os.path.expanduser(KEY_PATH) if KEY_PATH else None
if key_filename and not os.path.exists(key_filename):
    raise ValueError(f"SSH key file not found: {key_filename}")

with env() as client:
    with client.log_stream():
        client.storage.dut()
        print("Storage connected to DUT")
        client.power.cycle()
        print("DUT powered on")

        with client.serial.pexpect() as p:
            p.logfile = sys.stdout.buffer
            time.sleep(5)
            if not p.expect_exact("login:", timeout=600):
                p.sendline("")
            p.expect_exact("login:", timeout=30)
            print("Successfully showing login prompt via console")

            # password auth needs PermitRootLogin=yes to allow root password login.
            # (RHEL bootc defaults to prohibit-password which blocks root password login).
            if PASSWORD:
                print("Configuring SSH root password login via serial console...")
                # The first "login:" might match a systemd message during boot
                # Send Enter to get a fresh, reliable login prompt.
                time.sleep(2)
                p.sendline("")
                p.expect_exact("login:", timeout=30)
                p.sendline(USERNAME)
                p.expect("assword:", timeout=30)
                p.sendline(PASSWORD)
                # Wait for shell prompt (# for root, $ for non-root)
                p.expect(r"[#\$]", timeout=30)

                # Use 01- prefix so it's read FIRST by sshd (OpenSSH first-match-wins)
                p.sendline(
                    "echo 'PermitRootLogin yes' > /etc/ssh/sshd_config.d/01-permitrootlogin.conf"
                    " && chmod 644 /etc/ssh/sshd_config.d/01-permitrootlogin.conf"
                    " && systemctl restart sshd"
                    " && echo WRAPPER_SSH_CONFIG_OK"
                )
                p.expect_exact("WRAPPER_SSH_CONFIG_OK", timeout=30)
                print("SSH root login enabled and sshd restarted")

                p.sendline("exit")

        # Wait for SSH service to be fully ready after sshd restart
        print("Waiting for SSH service to start...")
        time.sleep(10)

        with TcpPortforwardAdapter(client=client.ssh.tcp) as addr:
            os.environ["JETSON_HOST"] = addr[0]
            os.environ["JETSON_PORT"] = str(addr[1])
            os.environ["JUMPSTARTER_IN_USE"] = "1"

            project_root = Path(__file__).parent.parent
            sys.path.insert(0, str(project_root))
            from infra_tests.ssh_client import SSHConnection

            with SSHConnection(
                addr[0],
                USERNAME,
                PASSWORD,
                addr[1],
                key_filename=key_filename,
            ) as ssh:
                ssh.sudo("/usr/libexec/bootc-generic-growpart")

            print(f"[wrapper] Launching pytest with JETSON_HOST={os.environ['JETSON_HOST']} "
                  f"JETSON_PORT={os.environ['JETSON_PORT']} "
                  f"JETSON_USERNAME={os.environ.get('JETSON_USERNAME')} "
                  f"JETSON_KEY_PATH={os.environ.get('JETSON_KEY_PATH', '(not set)')}")
            subprocess.run(sys.argv[1:])
