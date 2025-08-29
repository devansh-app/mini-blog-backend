import boto3
import os
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
import uuid
from flask import current_app

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.bucket_name = os.getenv('AWS_S3_BUCKET_NAME')
        
    def generate_presigned_url(self, file_extension, content_type, expires_in=3600):
      
        try:
            # Normalize the file 
            file_extension = file_extension.lower().strip()
            content_type = content_type.lower().strip()
            
            # to validate the content type
            if not self._validate_extension_content_type_match(file_extension, content_type):
                raise Exception(f"File extension '{file_extension}' does not match content type '{content_type}'")
            
            # generate a timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            file_key = f"posts/{timestamp}_{unique_id}.{file_extension}"
            
         
            current_app.logger.info(f"Generating presigned URL - Extension: {file_extension}, Content-Type: {content_type}, File-Key: {file_key}")
            
            # Generate presigned URL without ACL to avoid signature issues
            presigned_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_key,
                    'ContentType': content_type
                },
                ExpiresIn=expires_in
            )
            
            current_app.logger.info(f"Generated presigned URL successfully for {file_key}")
            
            return {
                'presigned_url': presigned_url,
                'file_key': file_key,
                'bucket_name': self.bucket_name,
                'expires_in': expires_in,
                'content_type': content_type
            }
            
        except ClientError as e:
            current_app.logger.error(f"Error generating presigned URL: {e}")
            raise Exception(f"Failed to generate presigned URL: {str(e)}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error in generate_presigned_url: {e}")
            raise Exception(f"Unexpected error: {str(e)}")
    
    def _validate_extension_content_type_match(self, file_extension, content_type):
 
        extension_content_type_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp'
        }
        
        expected_content_type = extension_content_type_map.get(file_extension)
        return expected_content_type == content_type
    
    def delete_file(self, file_key):
    
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            return True
        except ClientError as e:
            current_app.logger.error(f"Error deleting file from S3: {e}")
            return False
    
    def get_file_url(self, file_key):
 
        return f"https://{self.bucket_name}.s3.amazonaws.com/{file_key}"
    
    def set_file_public_read(self, file_key):

        try:
            self.s3_client.put_object_acl(
                Bucket=self.bucket_name,
                Key=file_key,
                ACL='public-read'
            )
            return True
        except ClientError as e:
            current_app.logger.error(f"Error setting file ACL: {e}")
            return False
    
    def validate_file_extension(self, file_extension):

        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
        return file_extension.lower() in allowed_extensions
    
    def validate_content_type(self, content_type):

        allowed_types = {
            'image/jpeg',
            'image/jpg', 
            'image/png',
            'image/gif',
            'image/webp'
        }
        return content_type.lower() in allowed_types
    
    def test_aws_connection(self):

        try:
            # Test bucket access
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            current_app.logger.info("AWS S3 connection successful")
            
            return {
                'status': 'success',
                'message': 'AWS S3 connection successful',
                'bucket_name': self.bucket_name,
                'region': os.getenv('AWS_REGION', 'us-east-1')
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            current_app.logger.error(f"AWS S3 connection failed: {error_code} - {error_message}")
            
            return {
                'status': 'error',
                'message': f"AWS S3 connection failed: {error_code} - {error_message}",
                'error_code': error_code,
                'bucket_name': self.bucket_name,
                'region': os.getenv('AWS_REGION', 'us-east-1')
            }
        except Exception as e:
            current_app.logger.error(f"AWS S3 connection failed: {str(e)}")
            
            return {
                'status': 'error',
                'message': f"AWS S3 connection failed: {str(e)}",
                'bucket_name': self.bucket_name,
                'region': os.getenv('AWS_REGION', 'us-east-1')
            }
