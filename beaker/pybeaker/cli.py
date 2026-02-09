"""
Wrapper for the bkr command-line client.

Provides a Python interface to bkr commands for:
- Job submission and management
- Workflow operations
- System operations
"""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CommandResult:
    """Result of a CLI command execution."""
    returncode: int
    stdout: str
    stderr: str
    command: list[str]
    
    @property
    def success(self) -> bool:
        return self.returncode == 0
    
    def check(self) -> "CommandResult":
        """Raise exception if command failed."""
        if not self.success:
            raise CLIError(
                f"Command failed with code {self.returncode}: "
                f"{' '.join(self.command)}\n{self.stderr}"
            )
        return self


class CLIError(Exception):
    """Error executing CLI command."""
    pass


class BeakerCLI:
    """Wrapper for the bkr command-line client.
    
    Example usage:
        >>> cli = BeakerCLI()
        >>> 
        >>> # Check who you are
        >>> result = cli.whoami()
        >>> print(result.stdout)
        >>> 
        >>> # Submit a job
        >>> job_id = cli.job_submit("job.xml")
        >>> 
        >>> # Create and submit a reservation workflow
        >>> job_id = cli.workflow_simple(
        ...     distro="RHEL-9.0",
        ...     arch="x86_64",
        ...     task="/distribution/check-install",
        ...     reserve=True,
        ...     reserve_duration=7200,
        ... )
    """
    
    def __init__(
        self,
        bkr_path: Optional[str] = None,
        hub_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """Initialize the CLI wrapper.
        
        Args:
            bkr_path: Path to bkr executable (default: find in PATH)
            hub_url: Override Beaker hub URL
            username: Username for authentication
            password: Password for authentication
        """
        self.bkr_path = bkr_path or shutil.which("bkr")
        if not self.bkr_path:
            raise CLIError(
                "bkr command not found in PATH. "
                "Install beaker-client: yum install beaker-client"
            )
        
        self.hub_url = hub_url
        self.username = username
        self.password = password
    
    def _run(
        self,
        *args: str,
        timeout: Optional[int] = None,
        input_data: Optional[str] = None,
    ) -> CommandResult:
        """Run a bkr command.
        
        Args:
            *args: Command arguments
            timeout: Command timeout in seconds
            input_data: Data to pass to stdin
            
        Returns:
            CommandResult with output
        """
        cmd = [self.bkr_path] + list(args)  # type: ignore
        
        # Add global options
        if self.hub_url:
            cmd.extend(["--hub", self.hub_url])
        if self.username:
            cmd.extend(["--username", self.username])
        if self.password:
            cmd.extend(["--password", self.password])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                input=input_data,
            )
            
            return CommandResult(
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                command=cmd,
            )
        except subprocess.TimeoutExpired:
            raise CLIError(f"Command timed out after {timeout} seconds")
        except FileNotFoundError:
            raise CLIError(f"bkr executable not found: {self.bkr_path}")
    
    def whoami(self) -> CommandResult:
        """Get the current authenticated user."""
        return self._run("whoami")
    
    def job_submit(
        self,
        job_xml: str | Path,
        wait: bool = False,
        dryrun: bool = False,
    ) -> str:
        """Submit a job from an XML file or string.
        
        Args:
            job_xml: Path to job XML file or XML string
            wait: Wait for job to complete
            dryrun: Don't actually submit, just validate
            
        Returns:
            Job ID (e.g., "J:12345")
        """
        args = ["job-submit"]
        
        if wait:
            args.append("--wait")
        if dryrun:
            args.append("--dryrun")
        
        # Check if it's a file path or XML string
        if isinstance(job_xml, Path):
            args.append(str(job_xml))
            result = self._run(*args)
        elif Path(job_xml).exists():
            args.append(job_xml)
            result = self._run(*args)
        else:
            # Assume it's XML content, write to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
                f.write(job_xml)
                temp_path = f.name
            try:
                args.append(temp_path)
                result = self._run(*args)
            finally:
                Path(temp_path).unlink(missing_ok=True)
        
        result.check()
        
        # Parse job ID from output
        import re
        match = re.search(r"J:\d+", result.stdout)
        if match:
            return match.group(0)
        return result.stdout.strip()
    
    def job_watch(
        self,
        job_id: str,
        timeout: Optional[int] = None,
    ) -> CommandResult:
        """Watch a job until completion.
        
        Args:
            job_id: Job ID (e.g., "J:12345")
            timeout: Maximum time to wait in seconds
            
        Returns:
            CommandResult with job status
        """
        args = ["job-watch", job_id]
        return self._run(*args, timeout=timeout)
    
    def job_cancel(self, job_id: str, message: Optional[str] = None) -> CommandResult:
        """Cancel a job.
        
        Args:
            job_id: Job ID
            message: Cancellation message
        """
        args = ["job-cancel", job_id]
        if message:
            args.extend(["--msg", message])
        
        return self._run(*args).check()
    
    def job_results(self, job_id: str, format: str = "json") -> CommandResult:
        """Get job results.
        
        Args:
            job_id: Job ID
            format: Output format ('json' or 'xml')
        """
        args = ["job-results", job_id]
        if format == "json":
            args.append("--format=json")
        
        return self._run(*args)
    
    def job_logs(self, job_id: str, output_dir: Optional[Path] = None) -> CommandResult:
        """Download job logs.
        
        Args:
            job_id: Job ID
            output_dir: Directory to save logs
        """
        args = ["job-logs", job_id]
        if output_dir:
            args.extend(["--output", str(output_dir)])
        
        return self._run(*args)
    
    def job_list(
        self,
        owner: Optional[str] = None,
        limit: int = 25,
        mine: bool = True,
    ) -> list[dict]:
        """List jobs.
        
        Args:
            owner: Filter by owner username
            limit: Maximum results
            mine: Show only my jobs (default True)
            
        Returns:
            List of job info dicts
        """
        args = ["job-list", "--limit", str(limit)]
        
        if mine and not owner:
            args.append("--mine")
        elif owner:
            args.extend(["--owner", owner])
        
        result = self._run(*args)
        result.check()
        
        # Parse output - typically one job ID per line
        jobs = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line and line.startswith("J:"):
                jobs.append({"job_id": line})
        
        return jobs
    
    def watchdog_extend(self, task_id: str, seconds: int) -> CommandResult:
        """Extend the watchdog time for a task.
        
        Args:
            task_id: Task ID (e.g., "T:12345")
            seconds: Seconds to extend by
        """
        return self._run("watchdog-extend", task_id, str(seconds)).check()
    
    def workflow_simple(
        self,
        distro: str,
        arch: str = "x86_64",
        task: str | list[str] = "/distribution/check-install",
        whiteboard: str = "pybeaker workflow",
        family: Optional[str] = None,
        variant: Optional[str] = None,
        machine: Optional[str] = None,
        hostrequire: Optional[list[str]] = None,
        keyvalue: Optional[list[str]] = None,
        reserve: bool = False,
        reserve_duration: Optional[int] = None,
        packages: Optional[list[str]] = None,
        repos: Optional[list[tuple[str, str]]] = None,
        dryrun: bool = False,
        wait: bool = False,
        debug: bool = False,
    ) -> str:
        """Run the workflow-simple command.
        
        Args:
            distro: Distro name
            arch: Architecture
            task: Task name(s) to run
            whiteboard: Job description
            family: Distro family filter
            variant: Distro variant filter
            machine: Specific machine hostname
            hostrequire: Host requirement filters
            keyvalue: Key-value pairs for host filtering
            reserve: Reserve system after completion
            reserve_duration: Reservation duration in seconds
            packages: Packages to install
            repos: List of (name, url) tuples for custom repos
            dryrun: Just print the XML, don't submit
            wait: Wait for job completion
            debug: Enable debug output
            
        Returns:
            Job ID (or XML if dryrun=True)
        """
        args = ["workflow-simple"]
        
        args.extend(["--distro", distro])
        args.extend(["--arch", arch])
        args.extend(["--whiteboard", whiteboard])
        
        # Tasks
        if isinstance(task, str):
            args.extend(["--task", task])
        else:
            for t in task:
                args.extend(["--task", t])
        
        # Distro filters
        if family:
            args.extend(["--family", family])
        if variant:
            args.extend(["--variant", variant])
        
        # Host filters
        if machine:
            args.extend(["--machine", machine])
        if hostrequire:
            for hr in hostrequire:
                args.extend(["--hostrequire", hr])
        if keyvalue:
            for kv in keyvalue:
                args.extend(["--keyvalue", kv])
        
        # Reservation
        if reserve:
            args.append("--reserve")
            if reserve_duration:
                args.extend(["--reserve-duration", str(reserve_duration)])
        
        # Packages
        if packages:
            for pkg in packages:
                args.extend(["--package", pkg])
        
        # Repos
        if repos:
            for name, url in repos:
                args.extend(["--repo", f"{name}={url}"])
        
        # Flags
        if dryrun:
            args.append("--dryrun")
        if wait:
            args.append("--wait")
        if debug:
            args.append("--debug")
        
        result = self._run(*args)
        
        if dryrun:
            return result.stdout
        
        result.check()
        
        # Parse job ID
        import re
        match = re.search(r"J:\d+", result.stdout)
        if match:
            return match.group(0)
        return result.stdout.strip()
    
    def system_status(self, fqdn: str) -> CommandResult:
        """Get system status."""
        return self._run("system-status", fqdn)
    
    def system_release(self, fqdn: str) -> CommandResult:
        """Release a system back to Beaker."""
        return self._run("system-release", fqdn)
    
    def system_reserve(self, fqdn: str) -> CommandResult:
        """Reserve a system manually."""
        return self._run("system-reserve", fqdn)
    
    def system_provision(
        self,
        fqdn: str,
        distro: str,
        kernel_options: Optional[str] = None,
        kickstart: Optional[Path] = None,
        reboot: bool = True,
    ) -> CommandResult:
        """Provision a system with a distro.
        
        Args:
            fqdn: System hostname
            distro: Distro name to provision
            kernel_options: Kernel boot options
            kickstart: Custom kickstart file
            reboot: Reboot after provisioning
        """
        args = ["system-provision", fqdn, "--distro", distro]
        
        if kernel_options:
            args.extend(["--kernel-options", kernel_options])
        if kickstart:
            args.extend(["--kickstart", str(kickstart)])
        if not reboot:
            args.append("--no-reboot")
        
        return self._run(*args).check()
    
    def distro_list(
        self,
        name: Optional[str] = None,
        family: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 25,
    ) -> list[str]:
        """List available distros.
        
        Args:
            name: Filter by name pattern
            family: Filter by family
            tag: Filter by tag
            limit: Maximum results
            
        Returns:
            List of distro names
        """
        args = ["distro-list", "--limit", str(limit)]
        
        if name:
            args.extend(["--name", name])
        if family:
            args.extend(["--family", family])
        if tag:
            args.extend(["--tag", tag])
        
        result = self._run(*args)
        result.check()
        
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    
    def task_list(
        self,
        package: Optional[str] = None,
        type: Optional[str] = None,
    ) -> list[str]:
        """List available tasks.
        
        Args:
            package: Filter by package
            type: Filter by type
            
        Returns:
            List of task names
        """
        args = ["task-list"]
        
        if package:
            args.extend(["--package", package])
        if type:
            args.extend(["--type", type])
        
        result = self._run(*args)
        result.check()
        
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

