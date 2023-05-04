resource "aws_cloudwatch_event_rule" "rate_1_minute" {
  name = "lambda_event_rule_rate_1_min"
  description = "retry scheduled every 1 min"
  schedule_expression = "rate(1 minute)"
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