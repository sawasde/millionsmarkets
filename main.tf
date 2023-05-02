resource "terraform_data" "cosmoagent_lambda_zip" {
  provisioner "local-exec" {
    command = "zip -r cosmoagent.zip cosmoagent utils"
    interpreter = ["/bin/bash", "-c"]
  }
}
