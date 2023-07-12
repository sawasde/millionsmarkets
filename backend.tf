terraform {
  backend "s3" {
    bucket = "mm-bots-s3-tfstate"
    key = "mm-bots-s3-tfstate/terraform.tfstate"
    region = "sa-east-1"
    dynamodb_table = "mm_bots_tfstate"
  }
}