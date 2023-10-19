provider "aws" {
  region = var.region
}

### COSMOAGENT IAC
### COSMOAGENT ZIP
resource "terraform_data" "cosmoagent_lambda_zip" {
  provisioner "local-exec" {
    command = "zip -r -X cosmoagent.zip cosmoagent utils"
    interpreter = ["/bin/bash", "-c"]
  }
}

### COSMOAGENT CRYPTO LAMBDA
resource "aws_lambda_function" "cosmoagent_crypto_lambda" {

  filename      = "cosmoagent.zip"
  function_name = "${terraform.workspace == "staging" ? "mm_cosmoagent_crypto_lambda_staging" : "mm_cosmoagent_crypto_lambda"}"
  role          = "${terraform.workspace == "staging" ? data.aws_iam_role.mm_bots_role_staging.arn : data.aws_iam_role.mm_bots_role.arn}"
  handler       = "cosmoagent.cosmoagent.launch"
  runtime       = "python3.9"
  memory_size   = 512
  timeout       = 60
  source_code_hash = filebase64sha256("cosmoagent.zip")

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
  function_name = "${terraform.workspace == "staging" ? "mm_cosmoagent_stock_lambda_staging" : "mm_cosmoagent_stock_lambda"}"
  role          = "${terraform.workspace == "staging" ? data.aws_iam_role.mm_bots_role_staging.arn : data.aws_iam_role.mm_bots_role.arn}"
  handler       = "cosmoagent.cosmoagent.launch"
  runtime       = "python3.9"
  memory_size   = 512
  timeout       = 60
  source_code_hash = filebase64sha256("cosmoagent.zip")


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

### COSMOAGENT ETF LAMBDA
resource "aws_lambda_function" "cosmoagent_etf_lambda" {

  filename      = "cosmoagent.zip"
  function_name = "${terraform.workspace == "staging" ? "mm_cosmoagent_etf_lambda_staging" : "mm_cosmoagent_etf_lambda"}"
  role          = "${terraform.workspace == "staging" ? data.aws_iam_role.mm_bots_role_staging.arn : data.aws_iam_role.mm_bots_role.arn}"
  handler       = "cosmoagent.cosmoagent.launch"
  runtime       = "python3.9"
  memory_size   = 512
  timeout       = 60
  source_code_hash = filebase64sha256("cosmoagent.zip")

  environment {
    variables = {
      TF_VAR_STAGING = var.STAGING
      TF_VAR_FROM_LAMBDA = var.FROM_LAMBDA
      TF_VAR_SYMBOL_TYPE = "ETF"
    }
  }

  layers = [ data.aws_lambda_layer_version.loguru_layer.arn,
             "arn:aws:lambda:sa-east-1:336392948345:layer:AWSSDKPandas-Python39:8" ] # AWS Pandas

  depends_on = [ terraform_data.cosmoagent_lambda_zip ]
}


### COSMO BOT IAC
### COSMOBOT CRYPTO & STOCK EC2
resource "aws_iam_instance_profile" "cosmobot_ec2_profile" {
  name = "${terraform.workspace == "staging" ? "mm_cosmobot_ec2_profile_staging" : "mm_cosmobot_ec2_profile"}"
  role = "${terraform.workspace == "staging" ? data.aws_iam_role.mm_bots_ec2_role_staging.name : data.aws_iam_role.mm_bots_ec2_role.name}"
}

data "template_file" "cosmobot_user_data" {
  template = "${file("cosmobot/setup.sh")}"

  vars = {
    TF_VAR_STAGING = var.STAGING
    TF_VAR_FROM_LAMBDA = "0"
    TF_VAR_COSMOBOT_DISCORD_CRYPTO_HOOK_URL = var.COSMOBOT_DISCORD_CRYPTO_HOOK_URL
    TF_VAR_COSMOBOT_DISCORD_STOCK_HOOK_URL = var.COSMOBOT_DISCORD_STOCK_HOOK_URL
    TF_VAR_COSMOBOT_DISCORD_ROLE = var.COSMOBOT_DISCORD_ROLE
    LOGS_FILENAME = "${terraform.workspace == "staging" ? "mm_cosmobot_staging.log" : "mm_cosmobot_prod.log"}"
    BRANCH = "${terraform.workspace == "staging" ? "staging" : "main"}"
  }
}

resource "aws_instance" "cosmobot_instance" {
    ami = "ami-0aba9f6e2597c6993" # ubuntu 20.04 arm64
    instance_type = "t4g.nano"
    vpc_security_group_ids = ["sg-0afa708ce5f1d4dd1"]
    associate_public_ip_address = "true"
    iam_instance_profile = "${aws_iam_instance_profile.cosmobot_ec2_profile.name}"
    user_data = "${data.template_file.cosmobot_user_data.rendered}"

    tags = {
      Name = "${terraform.workspace == "staging" ? "mm_cosmobot_ec2_staging" : "mm_cosmobot_ec2"}"
    }
}

### MONITORING IAC
resource "terraform_data" "monitoring_lambda_zip" {
  provisioner "local-exec" {
    command = "zip -r -X monitoring.zip monitoring utils"
    interpreter = ["/bin/bash", "-c"]
  }
}

resource "aws_lambda_function" "monitoring_lambda" {

  filename      = "monitoring.zip"
  function_name = "${terraform.workspace == "staging" ? "mm_monitoring_lambda_staging" : "mm_monitoring_lambda"}"
  role          = "${terraform.workspace == "staging" ? data.aws_iam_role.mm_bots_role_staging.arn : data.aws_iam_role.mm_bots_role.arn}"
  handler       = "monitoring.monitoring.launch"
  runtime       = "python3.9"
  memory_size   = 512
  timeout       = 600
  source_code_hash = filebase64sha256("monitoring.zip")

  environment {
    variables = {
      TF_VAR_STAGING = var.STAGING
      TF_VAR_FROM_LAMBDA = var.FROM_LAMBDA
      TF_VAR_MONITORING_DISCORD_HOOK_URL = var.MONITORING_DISCORD_HOOK_URL
      TF_VAR_MONITORING_DISCORD_ROLE = var.MONITORING_DISCORD_ROLE
    }
  }

  layers = [ data.aws_lambda_layer_version.loguru_layer.arn,
            "arn:aws:lambda:sa-east-1:336392948345:layer:AWSSDKPandas-Python39:8" ] # AWS Pandas

  depends_on = [ terraform_data.monitoring_lambda_zip ]
}
