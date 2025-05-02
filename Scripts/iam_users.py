# This code writes down the IAM users, their roles, used access keys and age, password age and group name and permissions and permision type 
#
# make sure to use the temporary access and secret key to get this code run on your local console
# 
# AWS configure 
#
# the output will be available as an easy, readable .csv file
import boto3
import csv

# Initialize boto3 client for IAM
iam_client = boto3.client('iam')

# Function to get all IAM users (paginated)
def get_all_users():
    users = []
    paginator = iam_client.get_paginator('list_users')
    
    # Paginate through all the users
    for page in paginator.paginate():
        users.extend(page['Users'])
    
    return users

# Function to get all roles (groups) for a specific user
def get_user_roles(user_name):
    roles = []
    paginator = iam_client.get_paginator('list_groups_for_user')
    
    # Paginate through all groups/roles for the user
    for page in paginator.paginate(UserName=user_name):
        roles.extend(page['Groups'])
    
    return [role['GroupName'] for role in roles]

# Function to get access keys for a specific user
def get_user_access_keys(user_name):
    access_keys = []
    paginator = iam_client.get_paginator('list_access_keys')
    
    # Paginate through all access keys for the user
    for page in paginator.paginate(UserName=user_name):
        access_keys.extend(page['AccessKeyMetadata'])
    
    return access_keys

# Function to get policies attached to the user (both inline and managed)
def get_user_policies(user_name):
    inline_policies = []
    managed_policies = []
    
    # Get inline policies for the user
    paginator_inline = iam_client.get_paginator('list_user_policies')
    for page in paginator_inline.paginate(UserName=user_name):
        inline_policies.extend(page['PolicyNames'])
    
    # Get managed policies for the user
    paginator_managed = iam_client.get_paginator('list_attached_user_policies')
    for page in paginator_managed.paginate(UserName=user_name):
        managed_policies.extend(page['AttachedPolicies'])
    
    # Format the policies in a list of tuples (PolicyName, PolicyType)
    policies = []
    
    # Add inline policies
    for policy in inline_policies:
        policies.append((policy, 'Inline'))
    
    # Add managed policies
    for policy in managed_policies:
        policies.append((policy['PolicyName'], 'Managed'))
    
    return policies

# Create and open the CSV file to write the output
with open('iam_users_info_with_policies_and_groups.csv', mode='w', newline='') as file:
    writer = csv.writer(file)
    # Write the header row
    writer.writerow(['UserName', 'GroupName(s)', 'RoleName', 'ConsoleAccess', 'AccessKeyID(s)', 'AccessKeyStatus', 'PermissionName(s)', 'PermissionType(s)'])

    # Get all IAM users
    users = get_all_users()

    for user in users:
        user_name = user['UserName']
        
        # Get the groups (roles) assigned to the user
        groups = get_user_roles(user_name)
        
        # Get the roles assigned to the user (groups in AWS terminology)
        roles = groups
        
        # Check if the user has console access
        user_info = iam_client.get_user(UserName=user_name)
        console_access = 'Yes' if 'PasswordLastUsed' in user_info['User'] else 'No'
        
        # Get the user's access keys
        access_keys = get_user_access_keys(user_name)
        
        # Prepare access key data
        if access_keys:
            access_key_ids = [key['AccessKeyId'] for key in access_keys]
            access_key_statuses = [key['Status'] for key in access_keys]
            access_keys_combined = ', '.join([f"{key_id} ({status})" for key_id, status in zip(access_key_ids, access_key_statuses)])
        else:
            access_keys_combined = 'None'

        # Get the user's policies
        policies = get_user_policies(user_name)
        
        # Prepare combined permissions (policy names and types)
        if policies:
            permission_names = [policy_name for policy_name, _ in policies]
            permission_types = [policy_type for _, policy_type in policies]
            permissions_combined = ', '.join(permission_names)
            permission_types_combined = ', '.join(permission_types)
        else:
            permissions_combined = 'None'
            permission_types_combined = 'None'

        # Write the user data to the CSV in a single row
        writer.writerow([user_name, ', '.join(groups), ', '.join(roles), console_access, access_keys_combined, 'Active' if access_keys_combined != 'None' else 'None', permissions_combined, permission_types_combined])

print('CSV file "iam_users_info_with_policies_and_groups.csv" has been created with IAM user details, policies, and groups.')
