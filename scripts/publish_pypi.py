import os
import subprocess
import sys


def publish(test_pypi: bool = False, token: str = None):
    dist_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
    if not os.path.exists(dist_dir) or not os.listdir(dist_dir):
        print("Building packages with 'python -m build'...")
        subprocess.run([sys.executable, "-m", "build"], check=True)

    cmd = [sys.executable, "-m", "twine", "upload"]
    if test_pypi:
        cmd.extend(["--repository", "testpypi"])
    cmd.append(f"{dist_dir}/*")

    env = os.environ.copy()
    if token:
        env["TWINE_USERNAME"] = "__token__"
        env["TWINE_PASSWORD"] = token

    print(f"Uploading to {'TestPyPI' if test_pypi else 'PyPI'}...")
    subprocess.run(cmd, env=env, check=True)


if __name__ == "__main__":
    is_test = "--test" in sys.argv
    api_token = os.environ.get("PYPI_TOKEN")
    publish(test_pypi=is_test, token=api_token)
