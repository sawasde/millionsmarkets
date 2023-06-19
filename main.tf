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
  role          = var.STAGING == "1" ? data.aws_iam_role.mm_bots_role_staging.arn : data.aws_iam_role.mm_lambda_role.arn
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
  role          = var.STAGING == "1" ? data.aws_iam_role.mm_bots_role_staging.arn : data.aws_iam_role.mm_lambda_role.arn
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

### COSMOAGENT ZIP
resource "terraform_data" "cosmobot_lambda_zip" {
  provisioner "local-exec" {
    command = "zip -r cosmobot.zip cosmobot utils"
    interpreter = ["/bin/bash", "-c"]
  }
}

### COSMOBOT CRYPTO LAMBDA
resource "aws_lambda_function" "cosmobot_crypto_lambda" {

  filename      = "cosmobot.zip"
  function_name = var.STAGING == "1" ? "cosmobot_crypto_lambda_staging" : "cosmobot_crypto_lambda"
  role          = var.STAGING == "1" ? data.aws_iam_role.mm_bots_role_staging.arn : data.aws_iam_role.mm_lambda_role.arn
  handler       = "cosmobot.cosmobot.launch"
  runtime       = "python3.9"
  memory_size   = 1024
  timeout       = 400

  environment {
    variables = {
      TF_VAR_STAGING = var.STAGING
      TF_VAR_FROM_LAMBDA = var.FROM_LAMBDA
      TF_VAR_COSMOBOT_DISCORD_CRYPTO_HOOK_URL = var.COSMOBOT_DISCORD_CRYPTO_HOOK_URL
      TF_VAR_COSMOBOT_DISCORD_ROLE = var.COSMOBOT_DISCORD_ROLE
      TF_VAR_SYMBOL_TYPE = "CRYPTO"
    }
  }

  layers = [data.aws_lambda_layer_version.loguru_layer.arn,
            "arn:aws:lambda:sa-east-1:336392948345:layer:AWSSDKPandas-Python39:8" ] # AWS Pandas

  depends_on = [ terraform_data.cosmobot_lambda_zip ]
}

### COSMOBOT STOCK LAMBDA
resource "aws_lambda_function" "cosmobot_stock_lambda" {

  filename      = "cosmobot.zip"
  function_name = var.STAGING == "1" ? "cosmobot_stock_lambda_staging" : "cosmobot_stock_lambda"
  role          = var.STAGING == "1" ? data.aws_iam_role.mm_bots_role_staging.arn : data.aws_iam_role.mm_lambda_role.arn
  handler       = "cosmobot.cosmobot.launch"
  runtime       = "python3.9"
  memory_size   = 1024
  timeout       = 400

  environment {
    variables = {
      TF_VAR_STAGING = var.STAGING
      TF_VAR_FROM_LAMBDA = var.FROM_LAMBDA
      TF_VAR_COSMOBOT_DISCORD_STOCK_HOOK_URL = var.COSMOBOT_DISCORD_STOCK_HOOK_URL
      TF_VAR_COSMOBOT_DISCORD_ROLE = var.COSMOBOT_DISCORD_ROLE
      TF_VAR_SYMBOL_TYPE = "STOCK"
    }
  }

  layers = [data.aws_lambda_layer_version.loguru_layer.arn,
            "arn:aws:lambda:sa-east-1:336392948345:layer:AWSSDKPandas-Python39:8" ] # AWS Pandas

  depends_on = [ terraform_data.cosmobot_lambda_zip ]
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
  role          = var.STAGING == "1" ? data.aws_iam_role.mm_bots_role_staging.arn : data.aws_iam_role.mm_lambda_role.arn
  handler       = "monitoring.monitoring.launch"
  runtime       = "python3.9"
  memory_size   = 1024
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

  depends_on = [ terraform_data.cosmobot_lambda_zip ]
}
