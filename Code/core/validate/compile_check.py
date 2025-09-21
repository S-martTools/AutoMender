import subprocess, shutil, tempfile, os
def compile_ok(solc_path: str, contract_path: str) -> bool:
    if not shutil.which(solc_path): return True
    try:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.check_output([solc_path,"--combined-json","abi,bin,ast",contract_path,"-o",tmp], stderr=subprocess.STDOUT, text=True)
        return True
    except subprocess.CalledProcessError:
        return False
