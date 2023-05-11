resource "aws_cloudwatch_event_rule" "rate_1_minute" {
  name = "lambda_event_rule_rate_1_min"
  description = "retry scheduled every 1 min"
  schedule_expression = "rate(1 minute)"
}

resource "aws_cloudwatch_event_rule" "rate_8_minutes" {
  name = "lambda_event_rule_rate_8_min"
  description = "retry scheduled every 8 min"
  schedule_expression = "rate(8 minutes)"
}

resource "aws_cloudwatch_event_target" "cosmoagent_trigger" {
  target_id = var.COSMOBOT_DEBUG == "1" ? "cosmoagent_event_lambda_test" : "cosmoagent_event_lambda"
  arn = aws_lambda_function.cosmoagent_lambda.arn
  rule = aws_cloudwatch_event_rule.rate_1_minute.name
}

resource "aws_lambda_permission" "allow_eventbridge_cosmoagent" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cosmoagent_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.rate_1_minute.arn
  statement_id  = "event_bridge_trigger_cosmoagent"
}

resource "aws_cloudwatch_event_target" "cosmobot_trigger" {
  target_id = var.COSMOBOT_DEBUG == "1" ? "cosmobot_event_lambda_test" : "cosmobot_event_lambda"
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