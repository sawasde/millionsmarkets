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

variable "COSMOBOT_DEBUG" {
    type = string
}

variable "COSMOBOT_FROM_LAMBDA" {
    type = string
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