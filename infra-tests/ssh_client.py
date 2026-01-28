"""
SSH client infrastructure for Jetson RPM tests using paramiko.
Based on test_basic_locally.py from edge-ai-image-pipelines.
"""
import logging
import socket
import time
import paramiko
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SSHConnection:
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
            hostname, port, username, timeout, key_filename or "password",
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
        # Step 2: Paramiko SSH connect (retry on timeout - lab links can be flaky)
        last_error = None
        connect_kw: dict = {
            "hostname": hostname,
            "port": port,
            "username": username,
            "timeout": timeout,
        }
        if key_filename:
            connect_kw["key_filename"] = key_filename
            connect_kw["password"] = password  # passphrase for encrypted key, or None
        else:
            connect_kw["password"] = password

        for attempt in range(1, 4):  # up to 3 attempts
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                logger.info("[SSH debug] Step 2: Paramiko connect (attempt %s/3) ...", attempt)
                self.client.connect(**connect_kw)
                logger.info("[SSH debug] Step 2: Paramiko connect OK")
                last_error = None
                break
            except (TimeoutError, OSError) as e:
                last_error = e
                try:
                    self.client.close()
                except Exception:
                    pass
                logger.warning("[SSH debug] Step 2 attempt %s/3 failed: %s", attempt, e)
                if attempt < 3:
                    time.sleep(2)
        if last_error is not None:
            logger.error("[SSH debug] Step 2 FAILED (Paramiko) after 3 attempts: %s", last_error, exc_info=True)
            raise last_error
        try:
            logger.info("[SSH debug] Step 3: open_sftp() ...")
            self.sftp = self.client.open_sftp()
            logger.info("[SSH debug] Step 3: open_sftp OK")
        except Exception as e:
            logger.error("[SSH debug] Step 3 FAILED (SFTP): %s", e, exc_info=True)
            self.client.close()
            raise
    
    def run(self, command: str, timeout: Optional[int] = None):
        """
        Run a command and return result with stdout attribute.
        
        Args:
            command: Command to execute
            timeout: Optional timeout in seconds
            
        Returns:
            Result object with stdout and exit_status attributes
        """
        stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8')
        error_output = stderr.read().decode('utf-8')
        
        # Create a result-like object similar to Fabric's result
        result = type('Result', (), {
            'stdout': output,
            'stderr': error_output,
            'exit_status': exit_status,
            'ok': exit_status == 0
        })()
        return result
    
    def sudo(self, command: str, timeout: Optional[int] = None, fail_on_rc: bool = True, expect_rc: Optional[int] = 0):
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
        
        result = self.run(f"sudo {command}", timeout=timeout)
        if fail_on_rc and result.exit_status != expect_rc:
            raise RuntimeError(f"Command '{command}' failed with exit status {result.exit_status}. Expected {expect_rc}.")
        return result
    
    def put(self, local_path: Path, remote_path: str):
        """
        Upload a file to remote host.
        
        Args:
            local_path: Local file path (Path object or string)
            remote_path: Remote file path
        """
        self.sftp.put(str(local_path), remote_path)
    
    def get(self, remote_path: str, local_path: Path):
        """
        Download a file from remote host.
        
        Args:
            remote_path: Remote file path
            local_path: Local file path (Path object or string)
        """
        self.sftp.get(remote_path, str(local_path))
    
    def close(self):
        """Close SSH connection."""
        if hasattr(self, 'sftp') and self.sftp:
            self.sftp.close()
        if hasattr(self, 'client') and self.client:
            self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
