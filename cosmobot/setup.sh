#!/bin/bash
# Setup env variables
echo "TF_VAR_STAGING=${TF_VAR_STAGING}" >> /etc/environment
echo "TF_VAR_FROM_LAMBDA=${TF_VAR_FROM_LAMBDA}" >> /etc/environment
echo "TF_VAR_COSMOBOT_DISCORD_CRYPTO_HOOK_URL=${TF_VAR_COSMOBOT_DISCORD_CRYPTO_HOOK_URL}" >> /etc/environment
echo "TF_VAR_COSMOBOT_DISCORD_ROLE=${TF_VAR_COSMOBOT_DISCORD_ROLE}" >> /etc/environment

echo "[+] Cloning project" >> "${LOGS_FILENAME}"
git clone -b "${BRANCH}" https://github.com/sawasde/millionsmarkets.git
cd millionsmarkets

echo "[+] Installing PIP" >> "${LOGS_FILENAME}"
curl -O https://bootstrap.pypa.io/get-pip.py
sudo python3 get-pip.py --user

echo "[+] Installing Dependencies" >> "${LOGS_FILENAME}"
sudo python3 -m pip install -r requirements.txt

echo "[+] Setup CLoudWatchLogs" >> "${LOGS_FILENAME}"
generate_config_file()
{
  cat <<EOF
{
  "agent": {
    "run_as_user": "ubuntu"
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/millionsmarkets/${LOGS_FILENAME}",
            "log_group_name": "mm_${LOGS_FILENAME}",
            "log_stream_name": "{instance_id}",
            "retention_in_days": 1
          }
        ]
      }
    }
  }
}
EOF
}
echo "$(generate_config_file)" > "logs_config.json"

echo "[+] Install Cloudwatch Agent" >> "${LOGS_FILENAME}"
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/arm64/latest/amazon-cloudwatch-agent.deb
sudo sudo dpkg -i -E ./amazon-cloudwatch-agent.deb
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/millionsmarkets/logs_config.json -s

echo "[+] Create Cron JOB" >> "${LOGS_FILENAME}"
sudo python3 -c "from cosmobot import cosmobotloop as cpl; cpl.launch()"