# TRIGGERS RULES
resource "aws_cloudwatch_event_rule" "rate_1_minute" {
  name = "lambda_event_rule_rate_1_min"
  description = "retry scheduled every 1 min"
  schedule_expression = "rate(1 minute)"
}

resource "aws_cloudwatch_event_rule" "rate_2_minutes" {
  name = "lambda_event_rule_rate_2_min"
  description = "retry scheduled every 2 min"
  schedule_expression = "rate(2 minute)"
}

resource "aws_cloudwatch_event_rule" "rate_8_minutes" {
  name = "lambda_event_rule_rate_8_min"
  description = "retry scheduled every 8 min"
  schedule_expression = "rate(8 minutes)"
}

resource "aws_cloudwatch_event_rule" "rate_20_minutes" {
  name = "lambda_event_rule_rate_20_min"
  description = "retry scheduled every 20 min"
  schedule_expression = "rate(20 minutes)"
}


# COSMOAGENT CRYPTO TRIGGERS
resource "aws_cloudwatch_event_target" "cosmoagent_crypto_trigger" {
  target_id = var.STAGING == "1" ? "cosmoagent_crypto_event_lambda_staging" : "cosmoagent_crypto_event_lambda"
  arn = aws_lambda_function.cosmoagent_crypto_lambda.arn
  rule = aws_cloudwatch_event_rule.rate_2_minutes.name
}

resource "aws_lambda_permission" "allow_eventbridge_cosmoagent_crypto" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cosmoagent_crypto_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.rate_2_minutes.arn
  statement_id  = "event_bridge_trigger_cosmoagent_crypto"
}

# COSMOBOT CRYPTO TRIGGERS
resource "aws_cloudwatch_event_target" "cosmobot_trigger" {
  target_id = var.STAGING == "1" ? "cosmobot_event_lambda_staging" : "cosmobot_event_lambda"
  arn = aws_lambda_function.cosmobot_lambda.arn
  rule = aws_cloudwatch_event_rule.rate_8_minutes.name
}

resource "aws_lambda_permission" "allow_eventbridge_cosmobot" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cosmobot_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.rate_8_minutes.arn
  statement_id  = "event_bridge_trigger_cosmobot"
}

# MONITORING TRIGGERS
resource "aws_cloudwatch_event_target" "monitoring_trigger" {
  target_id = var.STAGING == "1" ? "monitoring_event_lambda_staging" : "monitoring_event_lambda"
  arn = aws_lambda_function.monitoring_lambda.arn
  rule = aws_cloudwatch_event_rule.rate_20_minutes.name
}

resource "aws_lambda_permission" "allow_eventbridge_monitoring" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.monitoring_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.rate_20_minutes.arn
  statement_id  = "event_bridge_trigger_monitoring"
}