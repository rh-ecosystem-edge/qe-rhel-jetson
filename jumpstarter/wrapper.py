from jumpstarter.common.utils import env
from jumpstarter_driver_network.adapters import TcpPortforwardAdapter
import time
import sys
import os
import re
import subprocess
from pathlib import Path
from logging import getLogger

logger = getLogger(__name__)
USERNAME = os.environ.get("JETSON_USERNAME")
PASSWORD = os.environ.get("JETSON_PASSWORD")
KEY_PATH = os.environ.get("JETSON_KEY_PATH")

EXPECTED_RHEL_MAJOR = os.environ.get("EXPECTED_RHEL_MAJOR", "9") # expected rhel version
MAX_WRONG_OS_RETRIES = 2 # max number of times to try to fix the wrong OS
CI_DEFAULT_PASSWORD = "redhat"

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


def _detect_wrong_os(boot_output):
    """Check if device booted into wrong OS based on serial console output.

    Looks for RHEL version indicators in the text before the login: prompt.
    Returns (is_wrong, detected_version) tuple.
    """
    text = boot_output.decode("utf-8", errors="replace") if isinstance(boot_output, bytes) else str(boot_output)

    # Check for "Red Hat Enterprise Linux X.Y" in banner
    match = re.search(r'Enterprise Linux (\d+)', text)
    if match:
        booted_major = match.group(1)
        if booted_major != EXPECTED_RHEL_MAJOR:
            return True, booted_major

    # Check kernel version string for .elX pattern
    match = re.search(r'\.el(\d+)', text)
    if match:
        booted_major = match.group(1)
        if booted_major != EXPECTED_RHEL_MAJOR:
            return True, booted_major

    return False, None


def _fix_efi_via_serial(p):
    """Log into wrong OS and fix EFI boot entries to prioritize USB (/dev/sda).

    Uses CI default password ("redhat") to log into the NVMe OS, removes all
    existing RHEL boot entries, and creates a new entry for the USB disk.
    """
    logger.info("[wrapper] Logging into wrong OS to fix EFI boot entries...")

    # Get a fresh login prompt and log in with CI default password
    p.sendline("")
    p.expect_exact("login:", timeout=30)
    p.sendline("root")
    p.expect("assword:", timeout=30)
    p.sendline(CI_DEFAULT_PASSWORD)
    p.expect(r"[#\$]", timeout=30)
    logger.info("[wrapper] Logged into wrong OS with CI default password")

    # Remove all Red Hat / RHEL boot entries
    remove_cmd = (
        "for num in $(efibootmgr | grep -iE 'Red Hat|RHEL' "
        "| awk '{print substr($1,5,4)}'); "
        "do efibootmgr -b $num -B 2>/dev/null; done "
        "&& echo WRAPPER_EFI_REMOVE_OK"
    )
    p.sendline(remove_cmd)
    p.expect_exact("WRAPPER_EFI_REMOVE_OK", timeout=30)
    logger.info("[wrapper] Removed existing RHEL/Red Hat EFI boot entries")

    # Create new boot entry for USB disk (/dev/sda, partition 1)
    create_cmd = (
        "efibootmgr -c -d /dev/sda -p 1 -L 'RHEL Bootc Jumpstarter' "
        "-l '\\EFI\\redhat\\shimaa64.efi' "
        "&& echo WRAPPER_EFI_CREATE_OK"
    )
    p.sendline(create_cmd)
    p.expect_exact("WRAPPER_EFI_CREATE_OK", timeout=30)
    logger.info("[wrapper] Created new UEFI boot entry for USB (/dev/sda)")

    p.sendline("exit")
    time.sleep(2)
    logger.info("[wrapper] EFI boot fix complete, will power cycle to retry boot from USB")


def _wait_for_login(p):
    """Wait for login: prompt, handling grub> and dutlink recovery.

    Returns True if login prompt was reached, False otherwise.
    """
    got_login = False
    for attempt in range(3):
        try:
            idx = p.expect_exact(["login:", "grub>"], timeout=600)
            if idx == 0:
                got_login = True
                break
            else:
                logger.info(f"\n[wrapper] Device stuck at grub> (attempt {attempt + 1}/3), sending 'exit' to force reboot...")
                p.sendline("exit")
                time.sleep(10)
        except Exception:
            logger.info(f"\n[wrapper] Timeout waiting for login/grub (attempt {attempt + 1}/3), sending ENTER to probe for dutlink shell...")
            p.sendline("")
            try:
                idx = p.expect_exact(["#>", "login:", "grub>"], timeout=30)
                if idx == 0:
                    logger.info("[wrapper] Detected dutlink internal shell (#>), sending 'console' to re-enter serial console...")
                    p.sendline("console")
                    time.sleep(5)
                elif idx == 1:
                    got_login = True
                    break
                else:
                    logger.info("[wrapper] Got grub> after probe, sending 'exit'...")
                    p.sendline("exit")
                    time.sleep(10)
            except Exception:
                logger.info("[wrapper] No recognizable prompt after probe, retrying...")

    return got_login


with env() as client:
    with client.log_stream():

        for boot_attempt in range(MAX_WRONG_OS_RETRIES + 1):
            client.storage.dut()
            logger.info("[wrapper] Storage connected to DUT")
            client.power.cycle()
            logger.info("[wrapper] DUT powered on")

            with client.serial.pexpect() as p:
                p.logfile = sys.stdout.buffer
                time.sleep(30)

                if not _wait_for_login(p):
                    raise RuntimeError("[wrapper] Failed to reach login: prompt after recovery retries")

                # Check if device booted into the wrong OS (e.g., RHEL 10 from NVMe)
                wrong_os, detected_version = _detect_wrong_os(p.before)

                if wrong_os:
                    if boot_attempt >= MAX_WRONG_OS_RETRIES:
                        raise RuntimeError(
                            f"[wrapper] Device keeps booting wrong OS (RHEL {detected_version}) "
                            f"after {MAX_WRONG_OS_RETRIES} EFI fix attempts. "
                            f"Expected RHEL {EXPECTED_RHEL_MAJOR}."
                        )
                    logger.info(
                        f"[wrapper] Wrong OS detected: RHEL {detected_version} "
                        f"(expected RHEL {EXPECTED_RHEL_MAJOR}). "
                        f"Fixing EFI boot entries (attempt {boot_attempt + 1}/{MAX_WRONG_OS_RETRIES})..."
                    )
                    _fix_efi_via_serial(p)
                    continue  # exits serial context, loops back to power cycle

                # Correct OS — proceed with SSH configuration
                p.sendline("")
                p.expect_exact("login:", timeout=30)
                logger.info("[wrapper] Successfully showing login prompt via console")

                if PASSWORD:
                    logger.info("[wrapper] Configuring SSH root password login via serial console...")
                    time.sleep(2)
                    p.sendline("")
                    p.expect_exact("login:", timeout=30)
                    p.sendline(USERNAME)
                    p.expect("assword:", timeout=30)
                    p.sendline(PASSWORD)
                    p.expect(r"[#\$]", timeout=30)

                    p.sendline(
                        "echo 'PermitRootLogin yes' > /etc/ssh/sshd_config.d/01-permitrootlogin.conf"
                        " && chmod 644 /etc/ssh/sshd_config.d/01-permitrootlogin.conf"
                        " && systemctl restart sshd"
                        " && echo WRAPPER_SSH_CONFIG_OK"
                    )
                    p.expect_exact("WRAPPER_SSH_CONFIG_OK", timeout=30)
                    logger.info("[wrapper] SSH root login enabled and sshd restarted")

                    p.sendline("exit")

            # Correct OS booted and SSH configured — break out of retry loop
            break
        else:
            raise RuntimeError(
                f"[wrapper] Failed to boot correct OS (RHEL {EXPECTED_RHEL_MAJOR}) "
                f"after {MAX_WRONG_OS_RETRIES + 1} attempts"
            )

        # Wait for SSH service to be fully ready after sshd restart
        logger.info("[wrapper] Waiting for SSH service to start...")
        time.sleep(10)

        ssh_client = client.ssh.tcp if hasattr(client.ssh, 'tcp') else client.ssh
        with TcpPortforwardAdapter(client=ssh_client) as addr:
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

            logger.info(f"[wrapper] Launching pytest with JETSON_HOST={os.environ['JETSON_HOST']} "
                  f"JETSON_PORT={os.environ['JETSON_PORT']} "
                  f"JETSON_USERNAME={os.environ.get('JETSON_USERNAME')} "
                  f"JETSON_KEY_PATH={os.environ.get('JETSON_KEY_PATH', '(not set)')}")
            subprocess.run(sys.argv[1:])
