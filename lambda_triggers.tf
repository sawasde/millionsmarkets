# TRIGGERS RULES
resource "aws_cloudwatch_event_rule" "rate_1_minute" {
  name = "lambda_event_rule_rate_1_min"
  description = "retry scheduled every 1 min"
  schedule_expression = "rate(1 minute)"
}

resource "aws_cloudwatch_event_rule" "rate_2_minutes" {
  name = "lambda_event_rule_rate_2_min"
  description = "retry scheduled every 2 min"
  schedule_expression = "rate(2 minutes)"
}

resource "aws_cloudwatch_event_rule" "rate_4_minutes" {
  name = "lambda_event_rule_rate_4_min"
  description = "retry scheduled every 4 min"
  schedule_expression = "rate(4 minutes)"
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

resource "aws_cloudwatch_event_rule" "us_stock_market_4_minutes" {
  name = "lambda_event_rule_us_stock_market_4_minutes"
  description = "monday to friday from 9:00 am to 4:00pm UTC. each 4 minutes"
  schedule_expression = "cron(0/4 13-20 ? * MON-FRI *)"
}

resource "aws_cloudwatch_event_rule" "us_stock_market_2_minutes" {
  name = "lambda_event_rule_us_stock_market_2_minutes"
  description = "monday to friday from 9:00 am to 4:00pm UTC. each 2 minutes"
  schedule_expression = "cron(0/2 13-20 ? * MON-FRI *)"
}

# COSMOAGENT CRYPTO TRIGGERS
resource "aws_cloudwatch_event_target" "cosmoagent_crypto_trigger" {
  target_id = terraform.workspace == "staging" ? "mm_cosmoagent_crypto_event_lambda_staging" : "mm_cosmoagent_crypto_event_lambda"
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

# COSMOAGENT STOCK TRIGGERS
resource "aws_cloudwatch_event_target" "cosmoagent_stock_trigger" {
  target_id = terraform.workspace == "staging" ? "mm_cosmoagent_stock_event_lambda_staging" : "mm_cosmoagent_stock_event_lambda"
  arn = aws_lambda_function.cosmoagent_stock_lambda.arn
  rule = aws_cloudwatch_event_rule.us_stock_market_4_minutes.name
}

resource "aws_lambda_permission" "allow_eventbridge_cosmoagent_stock" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cosmoagent_stock_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.us_stock_market_4_minutes.arn
  statement_id  = "event_bridge_trigger_cosmoagent_stock"
}

# COSMOAGENT ETF TRIGGERS
resource "aws_cloudwatch_event_target" "cosmoagent_etf_trigger" {
  target_id = terraform.workspace == "staging" ? "mm_cosmoagent_etf_event_lambda_staging" : "mm_cosmoagent_etf_event_lambda"
  arn = aws_lambda_function.cosmoagent_etf_lambda.arn
  rule = aws_cloudwatch_event_rule.us_stock_market_4_minutes.name
}

resource "aws_lambda_permission" "allow_eventbridge_cosmoagent_etf" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cosmoagent_etf_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.us_stock_market_2_minutes.arn
  statement_id  = "event_bridge_trigger_cosmoagent_etf"
}

# MONITORING TRIGGERS
resource "aws_cloudwatch_event_target" "monitoring_trigger" {
  target_id = terraform.workspace == "staging" ? "mm_monitoring_event_lambda_staging" : "mm_monitoring_event_lambda"
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