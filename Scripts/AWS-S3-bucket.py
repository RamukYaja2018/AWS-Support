
""" This Python script generates a detailed summary report of all S3 buckets in an AWS account. It collects and writes information into a CSV file, including each bucket's name, creation date, region, 
and whether it has lifecycle rules enabled. 
For each bucket, it queries CloudWatch metrics to fetch the average size (over the past 3 days) for multiple S3 storage classes, converting the sizes into human-readable formats (e.g., GB, TB).
The code gracefully handles missing lifecycle configurations and region information. The final CSV provides 
a consolidated view of S3 storage usage, bucket metadata, and lifecycle rule presence, making it useful for auditing and cost optimization.
"""

import boto3
import botocore
import csv
from datetime import datetime, timedelta, timezone

STORAGE_CLASSES = [
    "StandardStorage",
    "GlacierStorage",
    "DeepArchiveStorage",
    "DeepArchiveObjectOverhead",
    "DeepArchiveS3ObjectOverhead",
    "StandardIAStorage",
    "IntelligentTieringFAStorage",
    "IntelligentTieringIAStorage"
]

def bytes_to_human_readable(size_bytes):
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"

s3 = boto3.client('s3')
buckets = s3.list_buckets()["Buckets"]

output = []
for bucket in buckets:
    name = bucket["Name"]
    created_date = bucket["CreationDate"].astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

    # Get region
    region = s3.get_bucket_location(Bucket=name)["LocationConstraint"]
    region = region if region else "us-east-1"

    # Check for lifecycle configuration (Yes/No)
    try:
        lifecycle = s3.get_bucket_lifecycle_configuration(Bucket=name)
        has_lifecycle = "Yes" if "Rules" in lifecycle and lifecycle["Rules"] else "No"
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchLifecycleConfiguration':
            has_lifecycle = "No"
        else:
            raise e  # re-raise unexpected errors

    # Create CloudWatch client in the bucket region
    cw = boto3.client('cloudwatch', region_name=region)

    row = {
        "Bucket": name,
        "CreatedDate": created_date,
        "Region": region,
        "LifecycleRules": has_lifecycle
    }

    for storage in STORAGE_CLASSES:
        try:
            size_stats = cw.get_metric_statistics(
                Namespace='AWS/S3',
                MetricName='BucketSizeBytes',
                Dimensions=[
                    {'Name': 'BucketName', 'Value': name},
                    {'Name': 'StorageType', 'Value': storage}
                ],
                StartTime=datetime.now(timezone.utc) - timedelta(days=3),
                EndTime=datetime.now(timezone.utc),
                Period=86400,
                Statistics=['Average']
            )
            size = size_stats['Datapoints'][0]['Average'] if size_stats['Datapoints'] else 0
        except:
            size = 0

        row[f"{storage}"] = bytes_to_human_readable(size)

    output.append(row)

# Write to CSV
with open("s3_storage_summary_full.csv", "w", newline="") as csvfile:
    fieldnames = ["Bucket", "CreatedDate", "Region", "LifecycleRules"] + STORAGE_CLASSES
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in output:
        writer.writerow(row)
