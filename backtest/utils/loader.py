import importlib.util
import os
import traceback
from types import ModuleType
from typing import List, Type, Optional, Callable
from backtest.exchange.dataclass.classdata import StrategyBase


def _find_python_files(directory: str) -> List[str]:
    """Find all .py plugin files in the directory and subdirectories."""
    python_files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(".py") and not filename.startswith("__"):
                python_files.append(os.path.join(root, filename))
    return python_files


def _get_valid_classes(module: ModuleType) -> List[Type[StrategyBase]]:
    """Extract all valid subclasses of StrategyBase from a module."""
    valid_classes = []
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and issubclass(attr, StrategyBase)
            and attr is not StrategyBase
            and not getattr(attr, "__exclude__", False)  # کلاس‌هایی که نمی‌خوای لود بشن
        ):
            setattr(attr, "__plugin_path__", getattr(module, "__file__", "نامشخص"))
            valid_classes.append(attr)
    return valid_classes

def _extract_metadata(cls: Type[StrategyBase]) -> str:
    """Read optional metadata from class docstring or attributes."""
    author = getattr(cls, "__author__", "No")
    version = getattr(cls, "__version__", "1.0")
    return f"Create By: {author} | version: {version}"

class StrategyLoader:
    def __init__(
        self,
        logger: Optional[Callable[[str], None]] = None,
        cache: bool = False,
    ):
        # Resolve strategies directory relative to project root (2 levels up from utils/)
        _utils_dir = os.path.dirname(os.path.abspath(__file__))
        _project_root = os.path.dirname(os.path.dirname(_utils_dir))
        self.generations_dir = os.path.join(_project_root, "strategies")
        self.logger = logger or print
        self.cache_enabled = cache
        self._strategies: List[Type[StrategyBase]] = []
        self._discovered = False

    def discover(self) -> List[Type[StrategyBase]]:
        """Discover all valid strategies from the plugin directory."""
        if self.cache_enabled and self._discovered:
            self._log("[💾] استفاده از کش فعال است. بارگذاری مجدد انجام نشد.")
            return self._strategies

        self._strategies.clear()

        plugin_files = _find_python_files(self.generations_dir.replace('/utils',''))

        self._log(f"[🔍] بررسی {len(plugin_files)} فایل پلاگین در مسیر: {self.generations_dir}")

        for file_path in plugin_files:
            module = self._import_module(file_path)
            if module:
                valid_classes = _get_valid_classes(module)
                self._strategies.extend(valid_classes)
                for cls in valid_classes:
                    meta_info = _extract_metadata(cls)
                    file_info = getattr(cls, "__plugin_path__", "No")
                    self._log(f"[✅] Class: {cls.__name__} | {meta_info} | File: {file_info}")

        self._log(f"[📦] تعداد نهایی کلاس‌های معتبر: {len(self._strategies)}")

        self._discovered = True
        return self._strategies

    def _import_module(self, file_path: str) -> Optional[ModuleType]:
        """Safely import a module from a given file path."""
        try:
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
        except Exception as e:
            self._log(f"[❌] خطا در ایمپورت {file_path}:\n{traceback.format_exc()} {e}")
        return None

    def _log(self, message: str):
        """Custom logger interface."""
        if self.logger:
            self.logger(message)
