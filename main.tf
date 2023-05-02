provider "aws" {
  region = var.region
}

variable region {
  type = string
  default = "sa-east-1"
}

data "aws_iam_role" "mm_lambda_role" {
  name = "lambda-mm-basic-role"
}

data "aws_lambda_layer_version" "binance_layer" {
  layer_name = "binance-layer"
}

data "aws_lambda_layer_version" "loguru_layer" {
  layer_name = "loguru-layer"
}

module "cosmoagent" {
  source = "./cosmoagent"
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
      foo = "bar"
    }
  }

  layers = [ data.aws_lambda_layer_version.binance_layer.arn,
            data.aws_lambda_layer_version.loguru_layer.arn,
            "arn:aws:lambda:sa-east-1:336392948345:layer:AWSSDKPandas-Python39:8" ] # AWS Pandas

  depends_on = [ terraform_data.cosmoagent_lambda_zip ]
}

### COSMO BOT