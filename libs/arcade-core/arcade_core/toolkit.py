import importlib.metadata
import importlib.util
import logging
import os
import types
from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator

from arcade_core.errors import ToolkitLoadError
from arcade_core.parse import get_tools_from_file

logger = logging.getLogger(__name__)


class Toolkit(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    """Name of the toolkit"""

    package_name: str
    """Name of the package holding the toolkit"""

    tools: dict[str, list[str]] = defaultdict(list)
    """Mapping of module names to tools"""

    # Other python package metadata
    version: str
    description: str
    author: list[str] = []
    repository: str | None = None
    homepage: str | None = None

    @field_validator("name", mode="before")
    def strip_arcade_prefix(cls, value: str) -> str:
        """
        Validator to strip the 'arcade_' prefix from the name if it exists.
        """
        return cls._strip_arcade_prefix(value)

    @classmethod
    def _strip_arcade_prefix(cls, value: str) -> str:
        """
        Strip the 'arcade_' prefix from the name if it exists.
        """
        if value.startswith("arcade_"):
            return value[len("arcade_") :]
        return value

    @classmethod
    def from_module(cls, module: types.ModuleType) -> "Toolkit":
        """
        Load a toolkit from an imported python module

        >>> import arcade_math
        >>> toolkit = Toolkit.from_module(arcade_math)
        """
        return cls.from_package(module.__name__)

    @classmethod
    def from_package(cls, package: str) -> "Toolkit":
        """
        Load a Toolkit from a Python package
        """
        try:
            metadata = importlib.metadata.metadata(package)
            name = metadata["Name"]
            package_name = package
            version = metadata["Version"]
            description = metadata.get("Summary", "")  # type: ignore[attr-defined]
            author = metadata.get_all("Author-email")
            homepage = metadata.get("Home-page", None)  # type: ignore[attr-defined]
            repo = metadata.get("Repository", None)  # type: ignore[attr-defined]

        except importlib.metadata.PackageNotFoundError as e:
            raise ToolkitLoadError(f"Package '{package}' not found.") from e
        except KeyError as e:
            raise ToolkitLoadError(f"Metadata key error for package '{package}'.") from e
        except Exception as e:
            raise ToolkitLoadError(f"Failed to load metadata for package '{package}'.") from e

        # Get the package directory
        try:
            package_dir = Path(get_package_directory(package))
        except (ImportError, AttributeError) as e:
            raise ToolkitLoadError(f"Failed to locate package directory for '{package}'.") from e

        # Get all python files in the package directory
        try:
            modules = [f for f in package_dir.glob("**/*.py") if f.is_file()]
        except OSError as e:
            raise ToolkitLoadError(
                f"Failed to locate Python files in package directory for '{package}'."
            ) from e

        toolkit = cls(
            name=name,
            package_name=package_name,
            version=version,
            description=description,
            author=author if author else [],
            homepage=homepage,
            repository=repo,
        )

        for module_path in modules:
            relative_path = module_path.relative_to(package_dir)
            import_path = ".".join(relative_path.with_suffix("").parts)
            import_path = f"{package_name}.{import_path}"
            toolkit.tools[import_path] = get_tools_from_file(str(module_path))

        if not toolkit.tools:
            raise ToolkitLoadError(f"No tools found in package {package}")

        return toolkit

    @classmethod
    def from_entrypoint(cls, entry: importlib.metadata.EntryPoint) -> "Toolkit":
        """
        Load a Toolkit from an entrypoint.

        The entrypoint value is used as the toolkit name, while the package name
        is extracted from the distribution that owns the entrypoint.

        Args:
            entry: The EntryPoint object from importlib.metadata

        Returns:
            A Toolkit instance

        Raises:
            ToolkitLoadError: If the toolkit cannot be loaded
        """
        # Get the package name from the distribution that owns this entrypoint
        if not hasattr(entry, "dist") or entry.dist is None:
            raise ToolkitLoadError(
                f"Entry point '{entry.name}' does not have distribution metadata. "
                f"This may indicate an incomplete package installation."
            )

        package_name = entry.dist.name

        toolkit = cls.from_package(package_name)
        toolkit.name = cls._strip_arcade_prefix(entry.value)

        return toolkit

    @classmethod
    def find_arcade_toolkits_from_entrypoints(cls) -> list["Toolkit"]:
        """
        Find and load as Toolkits all installed packages in the
        current Python interpreter's environment that have a
        registered entrypoint under the 'arcade.toolkits' group.
        """
        toolkits = []
        toolkit_entries: list[importlib.metadata.EntryPoint] = []

        try:
            toolkit_entries = importlib.metadata.entry_points(
                group="arcade_toolkits", name="toolkit_name"
            )
            for entry in toolkit_entries:
                try:
                    toolkit = cls.from_entrypoint(entry)
                    toolkits.append(toolkit)
                    logger.debug(
                        f"Loaded toolkit from entry point: {entry.name} = '{toolkit.name}'"
                    )
                except ToolkitLoadError as e:
                    logger.warning(
                        f"Warning: {e} Skipping toolkit from entry point '{entry.value}'"
                    )
        except Exception as e:
            logger.debug(f"Entry point discovery failed or not available: {e}")

        return toolkits

    @classmethod
    def find_arcade_toolkits_from_prefix(cls) -> list["Toolkit"]:
        """
        Find and load as Toolkits all installed packages in the
        current Python interpreter's environment that are prefixed with 'arcade_'.
        """
        import sysconfig

        toolkits = []
        site_packages_dir = sysconfig.get_paths()["purelib"]

        arcade_packages = [
            dist.metadata["Name"]
            for dist in importlib.metadata.distributions(path=[site_packages_dir])
            if dist.metadata["Name"].startswith("arcade_")
        ]

        for package in arcade_packages:
            try:
                toolkit = cls.from_package(package)
                toolkits.append(toolkit)
                logger.debug(f"Loaded toolkit from prefix discovery: {package}")
            except ToolkitLoadError as e:
                logger.warning(f"Warning: {e} Skipping toolkit {package}")

        return toolkits

    @classmethod
    def find_all_arcade_toolkits(cls) -> list["Toolkit"]:
        """
        Find and load as Toolkits all installed packages in the
        current Python interpreter's environment that either
        1. Have a registered entrypoint under the 'arcade.toolkits' group, or
        2. Are prefixed with 'arcade_'

        Returns:
            List[Toolkit]: A list of Toolkit instances.
        """
        # Find toolkits
        entrypoint_toolkits = cls.find_arcade_toolkits_from_entrypoints()
        prefix_toolkits = cls.find_arcade_toolkits_from_prefix()

        # Deduplicate. Entrypoints are preferred over prefix-based toolkits.
        seen_package_names = set()
        all_toolkits = []
        for toolkit in entrypoint_toolkits + prefix_toolkits:
            if toolkit.package_name not in seen_package_names:
                all_toolkits.append(toolkit)
                seen_package_names.add(toolkit.package_name)

        return all_toolkits


def get_package_directory(package_name: str) -> str:
    """
    Get the directory of a Python package
    """

    spec = importlib.util.find_spec(package_name)
    if spec is None:
        raise ImportError(f"Cannot find package named {package_name}")

    if spec.origin:
        # If the package has an origin, return the directory of the origin
        return os.path.dirname(spec.origin)
    elif spec.submodule_search_locations:
        # If the package is a namespace package, return the first search location
        return spec.submodule_search_locations[0]
    else:
        raise ImportError(f"Package {package_name} does not have a file path associated with it")
