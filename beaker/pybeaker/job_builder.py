"""
Fluent API for building Beaker job XML.

Provides a Pythonic way to construct job specifications with:
- Distro and host requirements
- Tasks and packages
- Reservation settings
- Multi-host configurations
"""

from dataclasses import dataclass, field
from typing import Any, Literal, Optional
from xml.etree import ElementTree as ET


ReserveWhen = Literal["always", "onabort", "onfail", "onwarn"]


@dataclass
class Task:
    """A task to run in a recipe."""
    name: str
    role: str = "STANDALONE"
    params: dict[str, str] = field(default_factory=dict)
    
    def to_xml(self) -> ET.Element:
        """Convert to XML element."""
        elem = ET.Element("task", name=self.name, role=self.role)
        
        if self.params:
            params_elem = ET.SubElement(elem, "params")
            for name, value in self.params.items():
                ET.SubElement(params_elem, "param", name=name, value=value)
        
        return elem


@dataclass
class HostFilter:
    """Filter criteria for selecting a host."""
    hostname: Optional[str] = None
    hostname_like: Optional[str] = None
    arch: Optional[str] = None
    hypervisor: Optional[str] = None  # Empty string for bare metal
    system_type: str = "Machine"
    memory_min: Optional[int] = None  # MB
    cpu_count_min: Optional[int] = None
    pool: Optional[str] = None
    force: Optional[str] = None  # Force specific system (admin only)
    
    # Device filters
    devices: list[dict[str, str]] = field(default_factory=list)
    
    def to_xml(self) -> ET.Element:
        """Convert to XML element."""
        elem = ET.Element("hostRequires")
        
        # If forcing a specific system
        if self.force:
            elem.set("force", self.force)
            return elem
        
        and_elem = ET.SubElement(elem, "and")
        
        # System type
        ET.SubElement(and_elem, "system_type", op="=", value=self.system_type)
        
        # Hostname
        if self.hostname:
            ET.SubElement(and_elem, "hostname", op="=", value=self.hostname)
        elif self.hostname_like:
            ET.SubElement(and_elem, "hostname", op="like", value=self.hostname_like)
        
        # Architecture
        if self.arch:
            ET.SubElement(and_elem, "arch", op="=", value=self.arch)
        
        # Hypervisor (empty = bare metal)
        if self.hypervisor is not None:
            ET.SubElement(and_elem, "hypervisor", op="=", value=self.hypervisor)
        
        # Memory
        if self.memory_min:
            ET.SubElement(and_elem, "memory", op=">=", value=str(self.memory_min))
        
        # CPU count
        if self.cpu_count_min:
            ET.SubElement(and_elem, "cpu_count", op=">=", value=str(self.cpu_count_min))
        
        # System pool
        if self.pool:
            ET.SubElement(and_elem, "pool", op="=", value=self.pool)
        
        # Devices
        for device in self.devices:
            ET.SubElement(and_elem, "device", **device)
        
        return elem


@dataclass
class DistroFilter:
    """Filter criteria for selecting a distro."""
    name: Optional[str] = None
    family: Optional[str] = None  # e.g., "RedHatEnterpriseLinux9"
    variant: Optional[str] = None  # e.g., "Server", "BaseOS"
    arch: Optional[str] = None
    method: Optional[str] = None  # e.g., "nfs", "http"
    tag: Optional[str] = None
    
    def to_xml(self) -> ET.Element:
        """Convert to XML element."""
        elem = ET.Element("distroRequires")
        and_elem = ET.SubElement(elem, "and")
        
        if self.name:
            ET.SubElement(and_elem, "distro_name", op="=", value=self.name)
        
        if self.family:
            ET.SubElement(and_elem, "distro_family", op="=", value=self.family)
        
        if self.variant:
            ET.SubElement(and_elem, "distro_variant", op="=", value=self.variant)
        
        if self.arch:
            ET.SubElement(and_elem, "distro_arch", op="=", value=self.arch)
        
        if self.method:
            ET.SubElement(and_elem, "distro_method", op="=", value=self.method)
        
        if self.tag:
            ET.SubElement(and_elem, "distro_tag", op="=", value=self.tag)
        
        return elem


@dataclass
class Recipe:
    """A recipe within a recipe set.
    
    Example:
        >>> recipe = (
        ...     Recipe(whiteboard="My test")
        ...     .with_distro(name="RHEL-9.0", arch="x86_64")
        ...     .with_host(hostname="myhost.example.com")
        ...     .with_package("vim")
        ...     .with_task("/distribution/check-install")
        ...     .with_reservation(duration=3600, when="onfail")
        ... )
    """
    whiteboard: str = ""
    role: str = "STANDALONE"
    kernel_options: str = ""
    kernel_options_post: str = ""
    ks_meta: str = ""
    
    distro: Optional[DistroFilter] = None
    host: Optional[HostFilter] = None
    packages: list[str] = field(default_factory=list)
    repos: list[dict[str, str]] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    
    # Reservation settings
    reserve: bool = False
    reserve_duration: int = 86400  # 24 hours
    reserve_when: ReserveWhen = "always"
    
    # Watchdog settings
    watchdog_panic: Optional[str] = None  # "ignore" to disable panic detection
    
    def with_distro(
        self,
        name: Optional[str] = None,
        family: Optional[str] = None,
        variant: Optional[str] = None,
        arch: Optional[str] = None,
        method: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> "Recipe":
        """Set distro requirements."""
        self.distro = DistroFilter(
            name=name,
            family=family,
            variant=variant,
            arch=arch,
            method=method,
            tag=tag,
        )
        return self
    
    def with_host(
        self,
        hostname: Optional[str] = None,
        hostname_like: Optional[str] = None,
        arch: Optional[str] = None,
        bare_metal: bool = False,
        memory_min: Optional[int] = None,
        cpu_count_min: Optional[int] = None,
        pool: Optional[str] = None,
        force: Optional[str] = None,
    ) -> "Recipe":
        """Set host requirements."""
        self.host = HostFilter(
            hostname=hostname,
            hostname_like=hostname_like,
            arch=arch,
            hypervisor="" if bare_metal else None,
            memory_min=memory_min,
            cpu_count_min=cpu_count_min,
            pool=pool,
            force=force,
        )
        return self
    
    def with_package(self, name: str) -> "Recipe":
        """Add a package to install."""
        self.packages.append(name)
        return self
    
    def with_packages(self, *names: str) -> "Recipe":
        """Add multiple packages to install."""
        self.packages.extend(names)
        return self
    
    def with_repo(self, name: str, url: str) -> "Recipe":
        """Add a custom repository."""
        self.repos.append({"name": name, "url": url})
        return self
    
    def with_task(
        self,
        name: str,
        role: str = "STANDALONE",
        **params: str,
    ) -> "Recipe":
        """Add a task to execute."""
        self.tasks.append(Task(name=name, role=role, params=params))
        return self
    
    def with_reservation(
        self,
        duration: int = 86400,
        when: ReserveWhen = "always",
    ) -> "Recipe":
        """Configure automatic reservation after tasks complete.
        
        Args:
            duration: Reservation duration in seconds (default 24 hours)
            when: When to reserve - 'always', 'onabort', 'onfail', or 'onwarn'
        """
        self.reserve = True
        self.reserve_duration = duration
        self.reserve_when = when
        return self
    
    def with_reservesys_task(
        self,
        duration: int = 86400,
        only_on_fail: bool = False,
    ) -> "Recipe":
        """Add the /distribution/reservesys task.
        
        This is an alternative to <reservesys/> element.
        
        Args:
            duration: Reservation time in seconds
            only_on_fail: Only reserve if recipe fails
        """
        params = {"RESERVETIME": str(duration)}
        if only_on_fail:
            params["RESERVE_IF_FAIL"] = "True"
        
        self.tasks.append(Task(
            name="/distribution/reservesys",
            role="STANDALONE",
            params=params,
        ))
        return self
    
    def to_xml(self) -> ET.Element:
        """Convert to XML element."""
        attrs: dict[str, str] = {"whiteboard": self.whiteboard}
        
        if self.role:
            attrs["role"] = self.role
        if self.kernel_options:
            attrs["kernel_options"] = self.kernel_options
        if self.kernel_options_post:
            attrs["kernel_options_post"] = self.kernel_options_post
        if self.ks_meta:
            attrs["ks_meta"] = self.ks_meta
        
        elem = ET.Element("recipe", **attrs)
        
        # Watchdog
        if self.watchdog_panic:
            ET.SubElement(elem, "watchdog", panic=self.watchdog_panic)
        
        # Distro requirements
        if self.distro:
            elem.append(self.distro.to_xml())
        
        # Host requirements
        if self.host:
            elem.append(self.host.to_xml())
        
        # Packages
        if self.packages:
            packages_elem = ET.SubElement(elem, "packages")
            for pkg in self.packages:
                ET.SubElement(packages_elem, "package", name=pkg)
        
        # Repos
        if self.repos:
            repos_elem = ET.SubElement(elem, "repos")
            for repo in self.repos:
                ET.SubElement(repos_elem, "repo", **repo)
        
        # Tasks
        for task in self.tasks:
            elem.append(task.to_xml())
        
        # Reservation
        if self.reserve:
            reserve_attrs: dict[str, str] = {"duration": str(self.reserve_duration)}
            if self.reserve_when != "always":
                reserve_attrs["when"] = self.reserve_when
            ET.SubElement(elem, "reservesys", **reserve_attrs)
        
        return elem


@dataclass
class RecipeSet:
    """A set of recipes that run simultaneously.
    
    Recipes in a set run concurrently on different systems,
    useful for multi-host testing (e.g., client/server).
    """
    recipes: list[Recipe] = field(default_factory=list)
    priority: Optional[str] = None  # "Low", "Medium", "Normal", "High", "Urgent"
    
    def add_recipe(self, recipe: Recipe) -> "RecipeSet":
        """Add a recipe to the set."""
        self.recipes.append(recipe)
        return self
    
    def to_xml(self) -> ET.Element:
        """Convert to XML element."""
        attrs = {}
        if self.priority:
            attrs["priority"] = self.priority
        
        elem = ET.Element("recipeSet", **attrs)
        
        for recipe in self.recipes:
            elem.append(recipe.to_xml())
        
        return elem


class JobBuilder:
    """Fluent builder for Beaker job XML.
    
    Example:
        >>> job = (
        ...     JobBuilder("My test job")
        ...     .with_group("my-team")
        ...     .add_recipe(
        ...         Recipe(whiteboard="Server")
        ...         .with_distro(name="RHEL-9.0", arch="x86_64")
        ...         .with_host(hostname="server.example.com")
        ...         .with_task("/distribution/check-install")
        ...         .with_reservation(duration=7200, when="onfail")
        ...     )
        ... )
        >>> print(job.to_xml())
    """
    
    def __init__(self, whiteboard: str = ""):
        """Initialize job builder.
        
        Args:
            whiteboard: Job description/name
        """
        self.whiteboard = whiteboard
        self.group: Optional[str] = None
        self.retention_tag: Optional[str] = None
        self.product: Optional[str] = None
        self.recipe_sets: list[RecipeSet] = []
        self._current_recipe_set: Optional[RecipeSet] = None
    
    def with_group(self, group: str) -> "JobBuilder":
        """Set the group for the job."""
        self.group = group
        return self
    
    def with_retention_tag(self, tag: str) -> "JobBuilder":
        """Set the retention tag."""
        self.retention_tag = tag
        return self
    
    def with_product(self, product: str) -> "JobBuilder":
        """Set the product."""
        self.product = product
        return self
    
    def add_recipe(self, recipe: Recipe) -> "JobBuilder":
        """Add a recipe in a new recipe set.
        
        Creates a new recipe set containing just this recipe.
        For multi-host scenarios, use add_recipe_set() instead.
        """
        recipe_set = RecipeSet(recipes=[recipe])
        self.recipe_sets.append(recipe_set)
        return self
    
    def add_recipe_set(self, recipe_set: RecipeSet) -> "JobBuilder":
        """Add a recipe set (for multi-host jobs)."""
        self.recipe_sets.append(recipe_set)
        return self
    
    def begin_recipe_set(self, priority: Optional[str] = None) -> "JobBuilder":
        """Begin a new recipe set for adding multiple recipes."""
        self._current_recipe_set = RecipeSet(priority=priority)
        return self
    
    def add_to_set(self, recipe: Recipe) -> "JobBuilder":
        """Add a recipe to the current recipe set."""
        if self._current_recipe_set is None:
            self.begin_recipe_set()
        self._current_recipe_set.add_recipe(recipe)  # type: ignore
        return self
    
    def end_recipe_set(self) -> "JobBuilder":
        """Finish the current recipe set and add it to the job."""
        if self._current_recipe_set:
            self.recipe_sets.append(self._current_recipe_set)
            self._current_recipe_set = None
        return self
    
    def build(self) -> ET.Element:
        """Build the job XML element tree."""
        # Close any open recipe set
        if self._current_recipe_set:
            self.end_recipe_set()
        
        attrs: dict[str, str] = {}
        if self.group:
            attrs["group"] = self.group
        if self.retention_tag:
            attrs["retention_tag"] = self.retention_tag
        if self.product:
            attrs["product"] = self.product
        
        job = ET.Element("job", **attrs)
        
        # Whiteboard
        wb = ET.SubElement(job, "whiteboard")
        wb.text = self.whiteboard
        
        # Recipe sets
        for recipe_set in self.recipe_sets:
            job.append(recipe_set.to_xml())
        
        return job
    
    def to_xml(self, pretty: bool = True) -> str:
        """Generate the job XML string.
        
        Args:
            pretty: Whether to format with indentation
            
        Returns:
            XML string
        """
        root = self.build()
        
        if pretty:
            ET.indent(root, space="  ")
        
        return ET.tostring(root, encoding="unicode", xml_declaration=False)


# Convenience functions for common job patterns

def simple_reservation_job(
    whiteboard: str,
    distro_name: str,
    arch: str = "x86_64",
    hostname: Optional[str] = None,
    duration: int = 86400,
    tasks: Optional[list[str]] = None,
) -> JobBuilder:
    """Create a simple job that reserves a system.
    
    Args:
        whiteboard: Job description
        distro_name: Name of the distro to install
        arch: Architecture (default x86_64)
        hostname: Specific host to reserve (optional)
        duration: Reservation duration in seconds
        tasks: List of task names to run before reservation
        
    Returns:
        JobBuilder instance ready to submit
    """
    recipe = (
        Recipe(whiteboard=whiteboard)
        .with_distro(name=distro_name, arch=arch)
        .with_reservation(duration=duration)
    )
    
    if hostname:
        recipe.with_host(hostname=hostname)
    
    if tasks:
        for task in tasks:
            recipe.with_task(task)
    else:
        recipe.with_task("/distribution/check-install")
    
    return JobBuilder(whiteboard).add_recipe(recipe)


def multihost_reservation_job(
    whiteboard: str,
    distro_name: str,
    hostnames: list[str],
    arch: str = "x86_64",
    duration: int = 86400,
) -> JobBuilder:
    """Create a multi-host job that reserves multiple systems.
    
    Args:
        whiteboard: Job description
        distro_name: Name of the distro to install
        hostnames: List of specific hosts to reserve
        arch: Architecture (default x86_64)
        duration: Reservation duration in seconds
        
    Returns:
        JobBuilder instance ready to submit
    """
    builder = JobBuilder(whiteboard).begin_recipe_set()
    
    for i, hostname in enumerate(hostnames):
        role = "SERVERS" if i == 0 else "CLIENTS"
        recipe = (
            Recipe(whiteboard=f"{whiteboard} - {hostname}", role=role)
            .with_distro(name=distro_name, arch=arch)
            .with_host(hostname=hostname)
            .with_task("/distribution/check-install")
            .with_reservation(duration=duration)
        )
        builder.add_to_set(recipe)
    
    return builder.end_recipe_set()

