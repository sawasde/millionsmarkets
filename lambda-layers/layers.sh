payload_path="payloads"
package_list=("discord.py") #"python-binance"  "loguru")
python_version="3.10"

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
if python3 --version 2>&1 | grep -q "Python $python_version"; then
  echo "[+] Python Version OK"
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

for pack in ${package_list[@]}; do

  echo "[+] Working with $pack Package"
  echo "[+] Creating $pack Virtual Env"
  python3 -m venv "$pack"

  echo "[+] Activating Virtual Env"
  source "$pack/bin/activate"

  echo "[+] Installing Package"
  pip install "$pack"

  echo "[+] Rename and Move Package"
  mv "$pack/lib/python3.10/site-packages" "$pack/python"

  echo "[+] Zipping Folder"
  cd $pack
  zip -r -q "$pack.zip" "python"
  cd ..

  echo "[+] Move Zip to root folder"
  mv "$pack/$pack.zip" "$pack.zip"

  echo "[+] Deactivating Virtual Env"
  deactivate
done