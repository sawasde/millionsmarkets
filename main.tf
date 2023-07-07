provider "aws" {
  region = var.region
}

### COSMOAGENT IAC
### COSMOAGENT ZIP
resource "terraform_data" "cosmoagent_lambda_zip" {
  provisioner "local-exec" {
    command = "zip -r cosmoagent.zip cosmoagent utils"
    interpreter = ["/bin/bash", "-c"]
  }
}

### COSMOAGENT CRYPTO LAMBDA
resource "aws_lambda_function" "cosmoagent_crypto_lambda" {

  filename      = "cosmoagent.zip"
  function_name = var.STAGING == "1" ? "cosmoagent_crypto_lambda_staging" : "cosmoagent_crypto_lambda"
  role          = var.STAGING == "1" ? data.aws_iam_role.mm_bots_role_staging.arn : data.aws_iam_role.mm_bots_role.arn
  handler       = "cosmoagent.cosmoagent.launch"
  runtime       = "python3.9"
  memory_size   = 512
  timeout       = 60

  environment {
    variables = {
      TF_VAR_BIN_API_KEY = var.BIN_API_KEY
      TF_VAR_BIN_API_SECRET = var.BIN_API_SECRET
      TF_VAR_STAGING = var.STAGING
      TF_VAR_FROM_LAMBDA = var.FROM_LAMBDA
      TF_VAR_SYMBOL_TYPE = "CRYPTO"
    }
  }

  layers = [ data.aws_lambda_layer_version.binance_layer.arn,
             data.aws_lambda_layer_version.loguru_layer.arn,
             "arn:aws:lambda:sa-east-1:336392948345:layer:AWSSDKPandas-Python39:8" ] # AWS Pandas

  depends_on = [ terraform_data.cosmoagent_lambda_zip ]
}

### COSMOAGENT STOCK LAMBDA
resource "aws_lambda_function" "cosmoagent_stock_lambda" {

  filename      = "cosmoagent.zip"
  function_name = var.STAGING == "1" ? "cosmoagent_stock_lambda_staging" : "cosmoagent_stock_lambda"
  role          = var.STAGING == "1" ? data.aws_iam_role.mm_bots_role_staging.arn : data.aws_iam_role.mm_bots_role.arn
  handler       = "cosmoagent.cosmoagent.launch"
  runtime       = "python3.9"
  memory_size   = 512
  timeout       = 60

  environment {
    variables = {
      TF_VAR_STAGING = var.STAGING
      TF_VAR_FROM_LAMBDA = var.FROM_LAMBDA
      TF_VAR_SYMBOL_TYPE = "STOCK"
    }
  }

  layers = [ data.aws_lambda_layer_version.loguru_layer.arn,
             "arn:aws:lambda:sa-east-1:336392948345:layer:AWSSDKPandas-Python39:8" ] # AWS Pandas

  depends_on = [ terraform_data.cosmoagent_lambda_zip ]
}

### COSMO BOT IAC
### COSMOBOT CRYPTO & STOCK EC2
resource "aws_iam_instance_profile" "cosmobot_ec2_profile" {
  name = var.STAGING == "1" ? "cosmobot_ec2_profile_staging" : "cosmobot_ec2_profile"
  role = var.STAGING == "1" ? data.aws_iam_role.mm_bots_ec2_role_staging.name : data.aws_iam_role.mm_bots_ec2_role.name
}

data "template_file" "cosmobot_user_data" {
  template = "${file("cosmobot/setup.sh")}"

  vars = {
    TF_VAR_STAGING = var.STAGING
    TF_VAR_FROM_LAMBDA = var.FROM_LAMBDA
    TF_VAR_COSMOBOT_DISCORD_CRYPTO_HOOK_URL = var.COSMOBOT_DISCORD_CRYPTO_HOOK_URL
    TF_VAR_COSMOBOT_DISCORD_ROLE = var.COSMOBOT_DISCORD_ROLE
    LOGS_FILENAME = var.STAGING == "1" ? "cosmobot_staging.log" : "cosmobot_prod.log"
  }
}

resource "aws_instance" "cosmobot_instance" {
    ami = "ami-0aba9f6e2597c6993" # ubuntu arm64
    instance_type = "t4g.nano"
    vpc_security_group_ids = ["sg-0afa708ce5f1d4dd1"]
    associate_public_ip_address = "true"
    iam_instance_profile = "${aws_iam_instance_profile.cosmobot_ec2_profile.name}"
    user_data = "${data.template_file.cosmobot_user_data.rendered}"

    tags = {
      Name = var.STAGING == "1" ? "cosmobot_ec2_staging" : "cosmobot_ec2"
    }
}

### MONITORING IAC
resource "terraform_data" "monitoring_lambda_zip" {
  provisioner "local-exec" {
    command = "zip -r monitoring.zip monitoring utils"
    interpreter = ["/bin/bash", "-c"]
  }
}

resource "aws_lambda_function" "monitoring_lambda" {

  filename      = "monitoring.zip"
  function_name = var.STAGING == "1" ? "monitoring_lambda_staging" : "monitoring_lambda"
  role          = var.STAGING == "1" ? data.aws_iam_role.mm_bots_role_staging.arn : data.aws_iam_role.mm_bots_role.arn
  handler       = "monitoring.monitoring.launch"
  runtime       = "python3.9"
  memory_size   = 512
  timeout       = 600

  environment {
    variables = {
      TF_VAR_STAGING = var.STAGING
      TF_VAR_FROM_LAMBDA = var.FROM_LAMBDA
      TF_VAR_MONITORING_DISCORD_HOOK_URL = var.MONITORING_DISCORD_HOOK_URL
    }
  }

  layers = [ data.aws_lambda_layer_version.loguru_layer.arn,
            "arn:aws:lambda:sa-east-1:336392948345:layer:AWSSDKPandas-Python39:8" ] # AWS Pandas

  depends_on = [ terraform_data.monitoring_lambda_zip ]
}
