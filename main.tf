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
  function_name = "cosmoagent_lambda"
  role          = data.aws_iam_role.mm_lambda_role.arn
  handler       = "cosmoagent.cosmoagent.launch"
  runtime       = "python3.9"

  environment {
    variables = {
      TF_VAR_BIN_API_KEY = var.BIN_API_KEY
      TF_VAR_BIN_API_SECRET = var.BIN_API_SECRET
      TF_VAR_COSMOBOT_DEBUG = var.COSMOBOT_DEBUG
      TF_VAR_COSMOBOT_FROM_LAMBDA = var.COSMOBOT_FROM_LAMBDA
    }
  }

  layers = [ data.aws_lambda_layer_version.binance_layer.arn,
            data.aws_lambda_layer_version.loguru_layer.arn,
            "arn:aws:lambda:sa-east-1:336392948345:layer:AWSSDKPandas-Python39:8" ] # AWS Pandas

  depends_on = [ terraform_data.cosmoagent_lambda_zip ]
}

### COSMO BOT