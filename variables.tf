variable region {
  type = string
  default = "sa-east-1"
}

variable "BIN_API_KEY" {
    type = string
}

variable "BIN_API_SECRET" {
    type = string
}

variable "STAGING" {
    type = string
}

variable "FROM_LAMBDA" {
    type = string
}

variable "COSMOBOT_DISCORD_CRYPTO_HOOK_URL" {
    type = string
}

variable "COSMOBOT_DISCORD_STOCK_HOOK_URL" {
    type = string
}

variable "MONITORING_DISCORD_HOOK_URL" {
    type = string
}

variable "COSMOBOT_DISCORD_ROLE" {
    type = string
}

data "aws_iam_role" "mm_lambda_role" {
  name = "mm_bots_role"
}

data "aws_iam_role" "mm_bots_role_staging" {
  name = "mm_bots_role_staging"
}

data "aws_lambda_layer_version" "binance_layer" {
  layer_name = "binance-layer"
}

data "aws_lambda_layer_version" "loguru_layer" {
  layer_name = "loguru-layer"
}