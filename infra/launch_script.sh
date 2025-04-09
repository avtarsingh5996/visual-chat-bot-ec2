#!/bin/bash
yum update -y
yum install -y python3 git
pip3 install --upgrade pip
mkdir /app
cd /app
git clone <YOUR_GITHUB_REPO_URL> .  # Replace with your repo URL
cd backend
pip3 install -r requirements.txt
export APPSYNC_API_ID=<APPSYNC_API_ID>  # Replace with actual ID or fetch from SSM
nohup python3 app.py &
