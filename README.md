# VisualChatBot (EC2 Deployment)

A real-time chatbot with a Ghibli-inspired 3D Sardar avatar on AWS EC2.

## Structure
- **backend/**: Flask app on EC2.
- **frontend/**: Web interface.
- **infra/**: CloudFormation template.

## Prerequisites
- AWS CLI configured (`aws configure`).
- EC2 key pair in ap-south-1.
- GitHub repo with this code.

## Deployment Steps
1. **Create Deployment Bucket**:
   ```bash
   aws s3 mb s3://visual-chatbot-deployment-296761184646 --region ap-south-1
