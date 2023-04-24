#!/bin/bash

payload_path="payloads"

declare -A package_dict
package_dict["binance"]="python-binance"
package_dict["discord"]="discord.py"
package_dict["loguru"]="loguru"

py_version="3.9"

# Check if a directory does not exist and create it
if [ ! -d "$payload_path" ] 
then
    echo "[+] Creating $payload_path directory"
    mkdir "$payload_path"
else
    echo "[+] Directory $payload_path exists." 
fi

cd "$payload_path"
# Ensure correct Python version
if "python$py_version" --version 2>&1 | grep -q "Python $py_version"; then
  echo "[+] Python Version OK python$py_version"
else
  echo "[-] Python Version FAIL. Please use the correct version"
  exit -1
fi

# Ensure zip is intalled
if which zip 2>&1 | grep -q "zip"; then
  echo "[+] zip OK"
else
  echo "[-] zip FAIL. Please install zip"
  exit -1
fi

function run_package() {
  echo "[+] Working with $1 Package. PIP package: $2"
  echo "[+] Creating $1 Virtual Env"
  "python$py_version" -m venv "$1"

  echo "[+] Activating Virtual Env"
  source "$1/bin/activate"

  echo "[+] Installing Package"
  pip install "$2"

  echo "[+] Rename and Move Package"
  mv "$1/lib/python$py_version/site-packages" "$1/python"

  echo "[+] Zipping Folder"
  cd $1
  zip -r -q "$1.zip" "python"
  cd ..

  echo "[+] Move Zip to root folder"
  mv "$1/$1.zip" "$1.zip"

  echo "[+] Deactivating Virtual Env"
  deactivate

  echo "[+] Finish $1"
  echo "[+] ---------------- [+]"
}

for pack in "${!package_dict[@]}"; do
  (run_package "$pack" "${package_dict[$pack]}")
done
