import os

sshpass = r"C:\Users\Victo\Hazard\backend\platform-tools-latest-windows\platform-tools\sshpass.exe"
ssh = r"C:\Windows\System32\OpenSSH\ssh.exe"
cmd = f'"{sshpass}" -p 5090 "{ssh}" -p 8022 -o StrictHostKeyChecking=no u0_a10443@localhost ls'

print(f"Running via os.system with FULL PATHS: {cmd}")
ret = os.system(cmd)
print(f"Return code: {ret}")
