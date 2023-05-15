provider "aws" {
  region = var.region
}

### COSMO AGENT IAC

resource "terraform_data" "cosmoagent_lambda_zip" {
  provisioner "local-exec" {
    command = "zip -r cosmoagent.zip cosmoagent utils"
    interpreter = ["/bin/bash", "-c"]
  }
}

resource "aws_lambda_function" "cosmoagent_lambda" {

  filename      = "cosmoagent.zip"
  function_name = var.COSMOBOT_STAGING == "1" ? "cosmoagent_lambda_qa" : "cosmoagent_lambda"
  role          = data.aws_iam_role.mm_lambda_role.arn
  handler       = "cosmoagent.cosmoagent.launch"
  runtime       = "python3.9"
  timeout       = 60

  environment {
    variables = {
      TF_VAR_BIN_API_KEY = var.BIN_API_KEY
      TF_VAR_BIN_API_SECRET = var.BIN_API_SECRET
      TF_VAR_COSMOBOT_STAGING = var.COSMOBOT_STAGING
      TF_VAR_COSMOBOT_FROM_LAMBDA = var.COSMOBOT_FROM_LAMBDA
    }
  }

  layers = [ data.aws_lambda_layer_version.binance_layer.arn,
            data.aws_lambda_layer_version.loguru_layer.arn,
            "arn:aws:lambda:sa-east-1:336392948345:layer:AWSSDKPandas-Python39:8" ] # AWS Pandas

  depends_on = [ terraform_data.cosmoagent_lambda_zip ]
}

### COSMO BOT IAC

resource "terraform_data" "cosmobot_lambda_zip" {
  provisioner "local-exec" {
    command = "zip -r cosmobot.zip cosmobot utils"
    interpreter = ["/bin/bash", "-c"]
  }
}

resource "aws_lambda_function" "cosmobot_lambda" {

  filename      = "cosmobot.zip"
  function_name = var.COSMOBOT_STAGING == "1" ? "cosmobot_lambda_test" : "cosmobot_lambda"
  role          = data.aws_iam_role.mm_lambda_role.arn
  handler       = "cosmobot.cosmobot.launch"
  runtime       = "python3.9"
  memory_size   = 1280
  timeout       = 200

  environment {
    variables = {
      TF_VAR_COSMOBOT_STAGING = var.COSMOBOT_STAGING
      TF_VAR_COSMOBOT_FROM_LAMBDA = var.COSMOBOT_FROM_LAMBDA
      TF_VAR_COSMOBOT_DISCORD_HOOK_URL = var.COSMOBOT_DISCORD_HOOK_URL
      TF_VAR_COSMOBOT_DISCORD_ROLE = var.COSMOBOT_DISCORD_ROLE
    }
  }

  layers = [ data.aws_lambda_layer_version.binance_layer.arn,
            data.aws_lambda_layer_version.loguru_layer.arn,
            "arn:aws:lambda:sa-east-1:336392948345:layer:AWSSDKPandas-Python39:8" ] # AWS Pandas

  depends_on = [ terraform_data.cosmobot_lambda_zip ]
}
