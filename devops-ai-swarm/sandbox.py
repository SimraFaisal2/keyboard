import os
import tempfile
import docker

def run_code_in_sandbox(code_string: str, test_string: str) -> dict:
    """
    Executes code and a pytest suite safely inside an isolated Docker container.
    """
    client = docker.from_env()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        app_path = os.path.join(tmpdir, "app.py")
        test_path = os.path.join(tmpdir, "test_app.py")
        
        with open(app_path, "w") as f:
            f.write(code_string)
            
        with open(test_path, "w") as f:
            f.write(test_string)
            
        try:
            container = client.containers.run(
                image="python:3.11-slim",
                command="sh -c 'pip install pytest && pytest test_app.py'",
                volumes={tmpdir: {"bind": "/app", "mode": "rw"}},
                working_dir="/app",
                detach=True
            )
            
            result = container.wait(timeout=30)
            logs = container.logs().decode("utf-8")
            container.remove()
            
            return {
                "success": result["StatusCode"] == 0,
                "output": logs,
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }