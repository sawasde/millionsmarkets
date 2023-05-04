resource "aws_cloudwatch_event_rule" "rate_1_minute" {
  name = "lambda-event-rule-rate-1-min"
  description = "retry scheduled every 1 min"
  schedule_expression = "rate(1 minute)"
}

resource "aws_cloudwatch_event_target" "cosmoagent_trigger" {
  target_id = "cosmoagent-event-target"
  arn = aws_lambda_function.cosmoagent_lambda.arn
  rule = aws_cloudwatch_event_rule.rate_1_minute.name
}

resource "aws_lambda_permission" "allow_eventbridge_cosmoagent" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cosmoagent_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.rate_1_minute.arn
  statement_id  = "event-bridge-trigger-cosmoagent"
}