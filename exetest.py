import subprocess
import os

def execute_inference(context):
    """
    runs local executable to perform inference
    """
    exe = '/root/minimal_generator/gpt2tc'
    command = [exe, '-m', '345M', 'g', str(context)]
    r = subprocess.run(command, stdout=subprocess.PIPE, cwd=os.path.split(exe)[0])
    out = str(r.stdout)
    out = out.replace("\\n", "\n")
    out = out.replace("\\'", "'")
    out = out.split("time=")[0]
    if "<|endoftext|>" in out:
        out = out.split("<|endoftext|>")[0]
    if out.startswith('b"') or out.startswith("b'"):
        out = out[2:]
    return out

print(execute_inference("Where do babies come from?"))