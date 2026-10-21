resource "aws_sns_topic" "alerts" {
  name = "opsboard-alerts"

  tags = {
    Name = "opsboard-alerts"
  }
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "alb_unhealthy_target" {
  alarm_name        = "opsboard-alb-unhealthy-target"
  alarm_description = "OpsBoard ALB has an unhealthy target"

  namespace   = "AWS/ApplicationELB"
  metric_name = "UnHealthyHostCount"
  statistic   = "Minimum"

  period              = 60
  evaluation_periods  = 2
  datapoints_to_alarm = 2

  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = aws_lb.opsboard.arn_suffix
    TargetGroup  = aws_lb_target_group.opsboard.arn_suffix
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  tags = {
    Name = "opsboard-alb-unhealthy-target"
  }
}

resource "aws_cloudwatch_metric_alarm" "ec2_status_check_failed" {
  alarm_name        = "opsboard-ec2-status-check-failed"
  alarm_description = "OpsBoard EC2 instance status check failed"

  namespace   = "AWS/EC2"
  metric_name = "StatusCheckFailed"
  statistic   = "Maximum"

  period              = 60
  evaluation_periods  = 2
  datapoints_to_alarm = 2

  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "missing"

  dimensions = {
    InstanceId = aws_instance.app.id
  }

  tags = {
    Name = "opsboard-ec2-status-check-failed"
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_low_storage" {
  alarm_name        = "opsboard-rds-low-storage"
  alarm_description = "OpsBoard RDS free storage is below 2 GiB"

  namespace   = "AWS/RDS"
  metric_name = "FreeStorageSpace"
  statistic   = "Minimum"

  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2

  threshold           = 2147483648
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "missing"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.opsboard.identifier
  }

  tags = {
    Name = "opsboard-rds-low-storage"
  }
}
