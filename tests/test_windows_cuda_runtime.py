import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from app import hardware
from app.windows_cuda_runtime import WINDOWS_CUDA_PACKAGES, _extract_runtime_wheel, _verify_staging


class WindowsCudaRuntimeTests(unittest.TestCase):
    def test_packages_are_exact_windows_wheels_with_sha256_pins(self):
        self.assertEqual(
            {package.component for package in WINDOWS_CUDA_PACKAGES},
            {"cuda_runtime", "cublas", "cudnn"},
        )
        for package in WINDOWS_CUDA_PACKAGES:
            self.assertTrue(package.filename.endswith("-win_amd64.whl"))
            self.assertEqual(len(package.sha256), 64)
            int(package.sha256, 16)

    def test_only_runtime_dlls_and_licences_are_extracted(self):
        names = {
            "cuda_runtime": "cudart64_12.dll",
            "cublas": "cublas64_12.dll",
            "cudnn": "cudnn64_9.dll",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staging = root / "staging"
            for package in WINDOWS_CUDA_PACKAGES:
                wheel = root / package.filename
                with zipfile.ZipFile(wheel, "w") as archive:
                    archive.writestr(f"nvidia/{package.component}/bin/{names[package.component]}", b"dll")
                    if package.component == "cublas":
                        archive.writestr("nvidia/cublas/bin/cublasLt64_12.dll", b"dll")
                    if package.component == "cudnn":
                        archive.writestr("nvidia/cudnn/bin/cudnn_ops64_9.dll", b"dll")
                    archive.writestr(f"{package.project}.dist-info/LICENSE.txt", b"licence")
                    archive.writestr("unrelated/module.py", b"not extracted")
                _extract_runtime_wheel(wheel, package, staging)

            _verify_staging(staging)
            self.assertFalse((staging / "unrelated" / "module.py").exists())
            self.assertTrue(any((staging / "licenses").rglob("LICENSE.txt")))

    def test_unsafe_wheel_member_is_rejected(self):
        package = WINDOWS_CUDA_PACKAGES[0]
        with tempfile.TemporaryDirectory() as temporary:
            wheel = Path(temporary) / package.filename
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("../escape.dll", b"bad")
                archive.writestr(f"nvidia/{package.component}/bin/cudart64_12.dll", b"dll")
            with self.assertRaisesRegex(RuntimeError, "Unsafe path"):
                _extract_runtime_wheel(wheel, package, Path(temporary) / "staging")

    def test_hardware_searches_per_user_cuda_runtime_first(self):
        with tempfile.TemporaryDirectory() as temporary:
            support = Path(temporary)
            runtime_bin = support / "cuda-runtime" / "bin"
            runtime_bin.mkdir(parents=True)
            with patch("app.hardware.platform.system", return_value="Windows"), patch(
                "app.hardware.app_support_dir", return_value=support
            ), patch("app.hardware.site.getsitepackages", return_value=[]), patch(
                "app.hardware.site.getusersitepackages", return_value=str(support / "site")
            ), patch.object(hardware.sys, "prefix", str(support / "prefix")):
                hardware._python_cuda_dll_dirs.cache_clear()
                directories = hardware._python_cuda_dll_dirs()
            hardware._python_cuda_dll_dirs.cache_clear()
            self.assertEqual(directories[0], runtime_bin)


if __name__ == "__main__":
    unittest.main()
