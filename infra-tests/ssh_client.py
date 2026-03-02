"""
SSH client infrastructure for Jetson RPM tests using paramiko.
Based on test_basic_locally.py from edge-ai-image-pipelines.
"""

import logging
import socket
import time
import paramiko
from fabric import Connection, Config
from typing import Optional
from tests import conftest as _conftest

logger = logging.getLogger(__name__)


class SSHConnection(Connection):
    """Simple SSH wrapper that mimics FabricAdapter interface for compatibility with existing tests."""

    def __init__(
        self,
        hostname: str,
        username: str,
        password: Optional[str],
        port: int = 22,
        timeout: int = 30,
        key_filename: Optional[str] = None,
    ):
        """
        Initialize SSH connection.

        Args:
            hostname: Hostname or IP address of the Jetson device
            username: SSH username
            password: SSH password (optional when using key_filename; used as key passphrase if key is encrypted)
            port: SSH port (default: 22)
            timeout: Connection timeout in seconds
            key_filename: Path to private key file (e.g. ~/.ssh/id_rsa). Use this when auth is key-based.
        """
        logger.info(
            "[SSH debug] Connecting: host=%s port=%s user=%s timeout=%ss key=%s",
            hostname,
            port,
            username,
            timeout,
            key_filename or "password",
        )

        # Step 1: quick TCP check (fails here if host unreachable or you need ProxyJump)
        try:
            logger.info("[SSH debug] Step 1: TCP connect to %s:%s ...", hostname, port)
            sock = socket.create_connection((hostname, port), timeout=timeout)
            sock.close()
            logger.info("[SSH debug] Step 1: TCP connect OK")
        except OSError as e:
            logger.error("[SSH debug] Step 1 FAILED (TCP): %s", e)
            raise

        # Step 2: initialize fabric.Connection
        connect_kwargs: dict = {}
        if key_filename:
            connect_kwargs["key_filename"] = key_filename
            connect_kwargs["passphrase"] = (
                password  # passphrase for encrypted key, or None
            )
            config = Config()
        elif password:
            connect_kwargs["password"] = password
            config = Config(
                overrides={"sudo": {"password": password}}
            )  # Use ssh password as sudo password
        else:
            raise ValueError("one of key_filename or password must be set")

        super().__init__(
            host=hostname,
            user=username,
            port=port,
            config=config,
            connect_timeout=timeout,
            connect_kwargs=connect_kwargs,
        )

        self.client.set_missing_host_key_policy(paramiko.WarningPolicy())

        # Step 3: Paramiko SSH connect (retry on timeout - lab links can be flaky)
        last_error = None
        for attempt in range(1, 4):  # up to 3 attempts
            try:
                logger.info(
                    "[SSH debug] Step 3: Paramiko connect (attempt %s/3) ...", attempt
                )
                self.open()
                logger.info("[SSH debug] Step 3: Paramiko connect OK")
                last_error = None
                break
            except (TimeoutError, OSError) as e:
                last_error = e
                logger.warning(
                    "[SSH debug] Step 3: Attempt %s/3 failed: %s", attempt, e
                )
                if attempt < 3:
                    time.sleep(2)
        if last_error is not None:
            logger.error(
                "[SSH debug] Step 3: FAILED (Paramiko) after 3 attempts: %s",
                last_error,
                exc_info=True,
            )
            raise last_error

        # Step 4: Paramiko SSH sftp
        try:
            logger.info("[SSH debug] Step 4: sftp() ...")
            self.sftp()
            logger.info("[SSH debug] Step 4: sftp() OK")
        except Exception as e:
            logger.error("[SSH debug] Step 4: FAILED (SFTP): %s", e, exc_info=True)
            raise

    def _mutate_command(self, command: str) -> str:
        MUTATING_DNF_COMMANDS = [
            "install",
            "remove",
            "update",
            "upgrade",
            "dist-sync",
            "group",
            "config-manager",
        ]
        # if bootc is available, add --transient to the dnf commands
        if _conftest.BOOTC_AVAILABLE:
            # Split the command into parts to check the actual sub-command accurately
            cmd_parts = command.split()
            if any(sub_cmd in cmd_parts for sub_cmd in MUTATING_DNF_COMMANDS):
                # Ensure we don't double-add the flag if it's already there
                if "--transient" not in command:
                    command += " --transient"
        return command

    def run(
        self,
        command: str,
        timeout: Optional[int] = None,
        fail_on_rc: bool = True,
        expect_rc: Optional[int] = 0,
        print_output: bool = True,
    ):
        """
        Run a command and return result with stdout attribute.

        Args:
            command: Command to execute
            timeout: Optional timeout in seconds

        Returns:
            Result object with stdout and exit_status attributes
        """
        command = self._mutate_command(command)

        if print_output:
            print("\t\tRunning command:", command)

        result = super().run(command, timeout=timeout, warn=True, hide=True)
        # Create a result-like object similar to Fabric's result
        result = type(
            "Result",
            (),
            {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_status": result.exited,
                "ok": result.exited == 0,
            },
        )()

        if print_output:
            print("\t\tstdout:", result.stdout)

        if fail_on_rc and result.exit_status != expect_rc:
            raise RuntimeError(
                f"Command '{command}' failed with exit status {result.exit_status}. Expected {expect_rc}. Error: {result.stderr}. \n\t\tOutput: {result.stdout}"
            )

        return result

    def sudo(
        self,
        command: str,
        timeout: Optional[int] = None,
        fail_on_rc: bool = True,
        expect_rc: Optional[int] = 0,
        print_output: bool = True,
    ):
        """
        Run a command with sudo.

        Args:
            command: Command to execute with sudo
            timeout: Optional timeout in seconds
            fail_on_rc: Whether to raise an exception if the command fails
            expect_rc: The expected exit status of the command
        Returns:
            Result object with stdout and exit_status attributes
        """
        command = self._mutate_command(command)

        if print_output:
            print("\t\tRunning command:", command)

        result = super().sudo(command, timeout=timeout, warn=True, hide=True)
        # Create a result-like object similar to Fabric's result
        result = type(
            "Result",
            (),
            {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_status": result.exited,
                "ok": result.exited == 0,
            },
        )()

        if print_output:
            print("\t\tstdout:", result.stdout)

        if fail_on_rc and result.exit_status != expect_rc:
            raise RuntimeError(
                f"Command '{command}' failed with exit status {result.exit_status}. Expected {expect_rc}. Error: {result.stderr}. \n\t\tOutput: {result.stdout}"
            )

        return result
