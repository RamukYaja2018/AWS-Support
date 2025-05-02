# Your script scans all S3 buckets in your AWS account and generates a CSV report listing the buckets that are potentially public.
#
# Specifically, those not fully blocking public access via the S3 "Block Public Access" configuration.
#
import boto3
import csv
from botocore.exceptions import ClientError

s3 = boto3.client('s3')

def is_public_block_disabled(bucket_name):
    try:
        response = s3.get_public_access_block(Bucket=bucket_name)
        config = response['PublicAccessBlockConfiguration']
        return not all(config.values())  # True if any flag is False
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchPublicAccessBlockConfiguration':
            return True  # No config means it's not blocking public access
        else:
            print(f"Error checking bucket {bucket_name}: {e}")
            return False

# Output filename
output_file = "public_s3_buckets.csv"

# Header
headers = ["Name", "AWS Region", "Access", "Creation Time"]

# Collect data
data = []

buckets = s3.list_buckets()['Buckets']
for bucket in buckets:
    name = bucket['Name']
    creation_time = bucket['CreationDate']

    if is_public_block_disabled(name):
        try:
            region = s3.get_bucket_location(Bucket=name).get('LocationConstraint') or "us-east-1"
        except ClientError as e:
            print(f"Error fetching region for bucket {name}: {e}")
            region = "Unknown"

        data.append([
            name,
            region,
            "Bucket is Public (Block all public access is disabled)",
            creation_time
        ])

# Write to CSV
with open(output_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(headers)
    writer.writerows(data)

print(f"[✓] CSV report generated: {output_file}")
