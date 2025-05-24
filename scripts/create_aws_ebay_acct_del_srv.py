### deply ebay marketplace account deletion server on aws
### from:
### https://github.com/mattkruse/Simple_AWS_Solution_eBay_Marketplace-account-deletion-notification/
import boto3
import secrets
import string
import json
import time
import os
import shutil
import subprocess
import logging


def generate_token(length=50):
    """Generate a secure verification token."""
    alphabet = string.ascii_letters + string.digits + "_-"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_lambda_package(verification_token, endpoint_url):
    """Create a zip package with the Lambda function."""
    # Create a temporary directory
    if os.path.exists("lambda_package"):
        shutil.rmtree("lambda_package")
    os.makedirs("lambda_package")

    # Create the Lambda handler file
    handler_code = f"""
import hashlib
import json
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

VERIFICATION_TOKEN = "{verification_token}"
ENDPOINT_URL = "{endpoint_url}"

def handler(event, context):
    try:
        logger.info(f"Received event: {{json.dumps(event)}}")
        
        # Handle GET request for challenge
        if event['httpMethod'] == 'GET':
            params = event.get('queryStringParameters', {{}})
            if not params or 'challenge_code' not in params:
                return {{
                    'statusCode': 400,
                    'body': json.dumps({{'error': 'Challenge code required'}})
                }}
                
            challenge_code = params['challenge_code']
            logger.info(f"Processing challenge code: {{challenge_code}}")
            
            # Concatenate in exact order: challenge_code + verification_token + endpoint_url
            input_string = challenge_code + VERIFICATION_TOKEN + ENDPOINT_URL
            logger.info(f"Input string for hash: {{input_string}}")
            
            # Generate SHA-256 hash
            challenge_response = hashlib.sha256(input_string.encode('utf-8')).hexdigest()
            logger.info(f"Generated challenge response: {{challenge_response}}")
            
            return {{
                'statusCode': 200,
                'headers': {{'Content-Type': 'application/json'}},
                'body': json.dumps({{'challengeResponse': challenge_response}})
            }}
            
        # Handle POST request for notifications
        elif event['httpMethod'] == 'POST':
            body = json.loads(event['body']) if event.get('body') else {{}}
            logger.info(f"Received notification: {{body}}")
            return {{
                'statusCode': 200,
                'body': json.dumps({{'status': 'ok'}})
            }}
            
        return {{
            'statusCode': 405,
            'body': json.dumps({{'error': 'Method not allowed'}})
        }}
            
    except Exception as e:
        logger.error(f"Error processing request: {{str(e)}}")
        return {{
            'statusCode': 500,
            'body': json.dumps({{'error': str(e)}})
        }}
"""

    with open("lambda_package/lambda_function.py", "w") as f:
        f.write(handler_code)

    # Create zip file
    shutil.make_archive("lambda_package", "zip", "lambda_package")

    # Read the zip file
    with open("lambda_package.zip", "rb") as f:
        zip_content = f.read()

    # Cleanup
    shutil.rmtree("lambda_package")
    os.remove("lambda_package.zip")

    return zip_content


def deploy():
    """Deploy the eBay notification handler to AWS Lambda and API Gateway."""
    # Generate verification token
    verification_token = generate_token()
    print("\nGenerated verification token")

    # Initialize AWS clients
    lambda_client = boto3.client("lambda")
    api_client = boto3.client("apigateway")
    iam_client = boto3.client("iam")
    sts_client = boto3.client("sts")
    print("Initialized AWS clients")

    # Get AWS account ID
    account_id = sts_client.get_caller_identity()["Account"]
    print(f"AWS Account ID: {account_id}")

    # Create or get IAM role
    role_name = "ebay-notification-lambda-role"
    try:
        role = iam_client.get_role(RoleName=role_name)
        role_arn = role["Role"]["Arn"]
        print("Using existing IAM role")
    except iam_client.exceptions.NoSuchEntityException:
        role = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
            ),
        )
        role_arn = role["Role"]["Arn"]

        # Attach basic Lambda execution policy
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )
        time.sleep(10)  # Wait for role propagation

    # Create API Gateway
    api = api_client.create_rest_api(
        name="ebay-notifications", endpointConfiguration={"types": ["REGIONAL"]}
    )

    # Get the root resource ID
    resources = api_client.get_resources(restApiId=api["id"])
    root_id = resources["items"][0]["id"]

    # Get the endpoint URL
    region = boto3.session.Session().region_name
    endpoint_url = f"https://{api['id']}.execute-api.{region}.amazonaws.com/prod"
    print(f"API Gateway endpoint: {endpoint_url}")

    # Create Lambda function
    function_name = "ebay-notification-handler"
    lambda_arn = lambda_client.create_function(
        FunctionName=function_name,
        Runtime="python3.11",
        Role=role_arn,
        Handler="lambda_function.handler",
        Code={"ZipFile": create_lambda_package(verification_token, endpoint_url)},
        Description="eBay notification handler",
        Timeout=30,
        MemorySize=128,
        Publish=True,
    )["FunctionArn"]
    print("Lambda function created/updated")

    # Create methods
    print("Setting up API methods...")
    for method in ["GET", "POST"]:
        api_client.put_method(
            restApiId=api["id"],
            resourceId=root_id,
            httpMethod=method,
            authorizationType="NONE",
        )

        api_client.put_integration(
            restApiId=api["id"],
            resourceId=root_id,
            httpMethod=method,
            type="AWS_PROXY",
            integrationHttpMethod="POST",
            uri=f"arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations",
        )

    # Create deployment
    api_client.create_deployment(restApiId=api["id"], stageName="prod")

    # Add Lambda permission
    source_arn = f'arn:aws:execute-api:{region}:{account_id}:{api["id"]}/*/*/*'
    print(f"Using source ARN: {source_arn}")
    try:
        lambda_client.add_permission(
            FunctionName=function_name,
            StatementId=f'api-gateway-{api["id"]}',
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com",
            SourceArn=source_arn,
        )
    except lambda_client.exceptions.ResourceConflictException:
        pass  # Permission already exists

    print("\n" + "=" * 50)
    print("✅ SETUP COMPLETE - SAVE THESE VALUES!")
    print("=" * 50)
    print(f"\n1. VERIFICATION TOKEN:\n{verification_token}")
    print(f"\n2. ENDPOINT URL:\n{endpoint_url}")
    print("\n" + "=" * 50)
    print("\nNext Steps:")
    print("1. Go to eBay Developer Portal")
    print("2. Navigate to Application Keys page")
    print("3. Click the Notifications link next to your App ID")
    print("4. Select 'Marketplace Account Deletion' radio button")
    print("5. Enter your alert email")
    print("6. Enter the Endpoint URL shown above")
    print("7. Enter the Verification Token shown above")
    print("8. Click Save")
    print("\n" + "=" * 50)


if __name__ == "__main__":
    deploy()
