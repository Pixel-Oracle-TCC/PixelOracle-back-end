#!/usr/bin/env bash
# Cria (ou reencontra) a EC2 t4g.micro da coleta. Não abre o Postgres na internet.
# Exige AWS CLI autenticado na conta de créditos. A chave fica em ~/.ssh, fora do git.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
NAME="pixel-oracle-coleta"
KEY_NAME="pixel-oracle-coleta"
KEY_PATH="${HOME}/.ssh/${KEY_NAME}.pem"
SG_NAME="pixel-oracle-coleta"

export AWS_DEFAULT_REGION="$REGION"
aws sts get-caller-identity >/dev/null

existing="$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=${NAME}" "Name=instance-state-name,Values=pending,running,stopped" \
  --query 'Reservations[0].Instances[0].InstanceId' --output text)"
if [ -n "$existing" ] && [ "$existing" != "None" ]; then
  state="$(aws ec2 describe-instances --instance-ids "$existing" --query 'Reservations[0].Instances[0].State.Name' --output text)"
  if [ "$state" = "stopped" ]; then
    aws ec2 start-instances --instance-ids "$existing" >/dev/null
    aws ec2 wait instance-running --instance-ids "$existing"
  fi
  ip="$(aws ec2 describe-instances --instance-ids "$existing" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)"
  echo "Instância já existe: ${existing} ${ip}"
  echo "Chave local: ${KEY_PATH}"
  exit 0
fi

if [ ! -f "$KEY_PATH" ]; then
  aws ec2 create-key-pair --key-name "$KEY_NAME" --query KeyMaterial --output text > "$KEY_PATH"
  chmod 600 "$KEY_PATH"
fi

vpc="$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)"
if [ -z "$vpc" ] || [ "$vpc" = "None" ]; then
  echo "Esta conta não tem VPC padrão. Crie uma na console antes de rodar de novo." >&2
  exit 1
fi

my_ip="$(curl -fsSL https://checkip.amazonaws.com | tr -d '[:space:]')"
sg="$(aws ec2 describe-security-groups --filters "Name=group-name,Values=${SG_NAME}" "Name=vpc-id,Values=${vpc}" --query 'SecurityGroups[0].GroupId' --output text)"
if [ -z "$sg" ] || [ "$sg" = "None" ]; then
  sg="$(aws ec2 create-security-group --group-name "$SG_NAME" --description "SSH da coleta Pixel Oracle" --vpc-id "$vpc" --query GroupId --output text)"
  aws ec2 authorize-security-group-ingress --group-id "$sg" --protocol tcp --port 22 --cidr "${my_ip}/32" >/dev/null
fi

ami="$(aws ssm get-parameter --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64 --query Parameter.Value --output text)"

instance="$(aws ec2 run-instances \
  --image-id "$ami" \
  --instance-type t4g.micro \
  --key-name "$KEY_NAME" \
  --security-group-ids "$sg" \
  --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":20,"VolumeType":"gp3"}}]' \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${NAME}}]" \
  --query 'Instances[0].InstanceId' --output text)"

aws ec2 wait instance-running --instance-ids "$instance"
ip="$(aws ec2 describe-instances --instance-ids "$instance" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)"
echo "EC2 ${instance} no ar: ${ip}"
echo "Chave: ${KEY_PATH}"
echo "SSH: ssh -i ${KEY_PATH} ec2-user@${ip}"
