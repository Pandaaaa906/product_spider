"""
服务管理器 - 用于测试时自动启动/停止服务

包含:
- ScrapydServiceManager: 管理 Scrapyd 服务
- ApiServiceManager: 管理 API Service

使用方法:
    from tests.service_manager import ScrapydServiceManager, ApiServiceManager

    with ScrapydServiceManager() as scrapyd:
        if scrapyd.is_running:
            # 运行测试
            pass

    with ApiServiceManager() as api:
        if api.is_running:
            # 运行测试
            pass
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from types import TracebackType


class BaseServiceManager:
    """服务管理器基类"""

    def __init__(self, service_url: str, max_wait: int = 30):
        self.service_url = service_url
        self.max_wait = max_wait
        self.process: subprocess.Popen | None = None
        self.is_running = False
        self._was_already_running = False

    def _is_service_running(self, check_endpoint: str = "/") -> bool:
        """检查服务是否已运行"""
        try:
            resp = requests.get(f"{self.service_url}{check_endpoint}", timeout=2)
            return resp.status_code in [200, 403]
        except Exception:
            return False

    def _wait_for_service(self, check_endpoint: str = "/") -> bool:
        """等待服务启动"""
        for i in range(self.max_wait):
            if self._is_service_running(check_endpoint):
                return True
            time.sleep(1)
            if i % 5 == 0:
                print(f"  等待服务启动... ({i}/{self.max_wait})")
        return False

    def start(self) -> bool:
        """启动服务 - 子类实现"""
        raise NotImplementedError

    def stop(self) -> None:
        """停止服务 - 子类实现"""
        raise NotImplementedError

    def __enter__(self) -> BaseServiceManager:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.stop()


class ScrapydServiceManager(BaseServiceManager):
    """Scrapyd 服务管理器

    自动启动/停止 Scrapyd 服务，支持上下文管理器。

    用法:
        with ScrapydServiceManager() as mgr:
            if mgr.is_running:
                # 运行测试
                pass
    """

    def __init__(
        self,
        scrapyd_url: str = "http://127.0.0.1:6800",
        max_wait: int = 30,
        use_uv: bool = True,
    ):
        super().__init__(scrapyd_url, max_wait)
        self.use_uv = use_uv

    def start(self) -> bool:
        """启动 Scrapyd 服务"""
        # 检查是否已运行
        if self._is_service_running("/daemonstatus.json"):
            print(f"[INFO] Scrapyd 已在运行: {self.service_url}")
            self.is_running = True
            self._was_already_running = True
            return True

        print(f"[INFO] 启动 Scrapyd...")

        # 使用 uv run 启动
        cmd = ["uv", "run", "--env-file=./test.local.env", "scrapyd"]

        try:
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

            project_root = Path(__file__).parent.parent
            self.process = subprocess.Popen(
                cmd,
                cwd=str(project_root),
                **kwargs
            )

            # 等待服务就绪
            if self._wait_for_service("/daemonstatus.json"):
                print(f"[OK] Scrapyd 启动成功 (PID: {self.process.pid})")
                self.is_running = True
                return True
            else:
                print(f"[ERROR] Scrapyd 在 {self.max_wait} 秒内未启动")
                self.stop()
                return False

        except Exception as e:
            print(f"[ERROR] 启动 Scrapyd 失败: {e}")
            return False

    def stop(self) -> None:
        """停止 Scrapyd 服务"""
        if self._was_already_running:
            print(f"[INFO] Scrapyd 原本就在运行，不停止")
            return

        if self.process is None:
            return

        print(f"[INFO] 停止 Scrapyd...")
        try:
            if sys.platform == "win32":
                self.process.send_signal(subprocess.signal.CTRL_BREAK_EVENT)
            else:
                self.process.terminate()

            try:
                self.process.wait(timeout=10)
                print(f"[OK] Scrapyd 已停止")
            except subprocess.TimeoutExpired:
                print(f"[WARN] Scrapyd 未正常停止，强制终止...")
                self.process.kill()
                self.process.wait()
                print(f"[OK] Scrapyd 已强制终止")

        except Exception as e:
            print(f"[WARN] 停止 Scrapyd 出错: {e}")
        finally:
            self.process = None
            self.is_running = False


class ApiServiceManager(BaseServiceManager):
    """API Service 服务管理器

    自动启动/停止 API Service，支持上下文管理器。

    用法:
        with ApiServiceManager() as mgr:
            if mgr.is_running:
                # 运行测试
                pass
    """

    def __init__(
        self,
        api_url: str = "http://127.0.0.1:18000",
        max_wait: int = 30,
        use_uv: bool = True,
    ):
        super().__init__(api_url, max_wait)
        self.use_uv = use_uv

    def start(self) -> bool:
        """启动 API Service"""
        # 检查是否已运行
        if self._is_service_running("/docs"):
            print(f"[INFO] API Service 已在运行: {self.service_url}")
            self.is_running = True
            self._was_already_running = True
            return True

        print(f"[INFO] 启动 API Service...")

        # 使用 uv run 启动
        cmd = [
            "uv", "run",
            "uvicorn", "api_service.main:app",
            "--host", "0.0.0.0",
            "--port", "18000"
        ]

        try:
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

            project_root = Path(__file__).parent.parent
            self.process = subprocess.Popen(
                cmd,
                cwd=str(project_root),
                **kwargs
            )

            # 等待服务就绪
            if self._wait_for_service("/docs"):
                print(f"[OK] API Service 启动成功 (PID: {self.process.pid})")
                self.is_running = True
                return True
            else:
                print(f"[ERROR] API Service 在 {self.max_wait} 秒内未启动")
                self.stop()
                return False

        except Exception as e:
            print(f"[ERROR] 启动 API Service 失败: {e}")
            return False

    def stop(self) -> None:
        """停止 API Service"""
        if self._was_already_running:
            print(f"[INFO] API Service 原本就在运行，不停止")
            return

        if self.process is None:
            return

        print(f"[INFO] 停止 API Service...")
        try:
            if sys.platform == "win32":
                self.process.send_signal(subprocess.signal.CTRL_BREAK_EVENT)
            else:
                self.process.terminate()

            try:
                self.process.wait(timeout=10)
                print(f"[OK] API Service 已停止")
            except subprocess.TimeoutExpired:
                print(f"[WARN] API Service 未正常停止，强制终止...")
                self.process.kill()
                self.process.wait()
                print(f"[OK] API Service 已强制终止")

        except Exception as e:
            print(f"[WARN] 停止 API Service 出错: {e}")
        finally:
            self.process = None
            self.is_running = False


class ServiceManager:
    """组合服务管理器 - 同时管理多个服务

    用法:
        with ServiceManager() as mgr:
            if mgr.all_running:
                # 运行测试
                pass
    """

    def __init__(
        self,
        scrapyd_url: str = "http://127.0.0.1:6800",
        api_url: str = "http://127.0.0.1:8000",
        max_wait: int = 30,
    ):
        self.scrapyd = ScrapydServiceManager(scrapyd_url, max_wait)
        self.api = ApiServiceManager(api_url, max_wait)
        self.all_running = False

    def start(self) -> bool:
        """启动所有服务"""
        scrapyd_ok = self.scrapyd.start()
        api_ok = self.api.start()
        self.all_running = scrapyd_ok and api_ok
        return self.all_running

    def stop(self) -> None:
        """停止所有服务"""
        self.api.stop()
        self.scrapyd.stop()
        self.all_running = False

    def __enter__(self) -> ServiceManager:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.stop()
