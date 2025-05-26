# main.tf
provider "aws" {
  region = "us-east-1"
}

# Fetch VPC and subnets (modify filters if needed)
data "aws_vpc" "main" {
  default = true
}

data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.main.id]
  }
}

# Get EC2 instances with a specific tag
data "aws_instances" "target_instances" {
  filter {
    name   = "tag:AutoRegister"
    values = ["true"]
  }
}

# Security group for ALB
resource "aws_security_group" "alb_sg" {
  name        = "alb-sg"
  description = "Allow HTTP"
  vpc_id      = data.aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ALB
resource "aws_lb" "app_alb" {
  name               = "auto-app-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = data.aws_subnets.public.ids
}

# Target group
resource "aws_lb_target_group" "tg" {
  name     = "auto-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = data.aws_vpc.main.id
  target_type = "instance"
  health_check {
    path = "/"
    protocol = "HTTP"
  }
}

# Listener
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app_alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.tg.arn
  }
}

# Register instances dynamically
resource "aws_lb_target_group_attachment" "register_instances" {
  for_each = toset(data.aws_instances.target_instances.ids)

  target_group_arn = aws_lb_target_group.tg.arn
  target_id        = each.value
  port             = 80
}
