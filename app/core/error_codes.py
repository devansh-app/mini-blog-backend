"""
Centralized error codes and messages for the application
"""

class ErrorCodes:
    # Authentication Errors (1000-1099)
    INVALID_CREDENTIALS = 1000
    USER_NOT_FOUND = 1001
    USERNAME_TAKEN = 1002
    EMAIL_TAKEN = 1003
    INVALID_TOKEN = 1004
    TOKEN_EXPIRED = 1005
    UNAUTHORIZED = 1006
    INVALID_REFRESH_TOKEN = 1007
    
    # Validation Errors (1100-1199)
    MISSING_REQUIRED_FIELDS = 1100
    INVALID_USERNAME_LENGTH = 1101
    INVALID_PASSWORD_LENGTH = 1102
    INVALID_EMAIL_FORMAT = 1103
    INVALID_POST_TITLE_LENGTH = 1104
    INVALID_POST_CONTENT_LENGTH = 1105
    INVALID_COMMENT_LENGTH = 1106
    
    # Resource Errors (1200-1299)
    POST_NOT_FOUND = 1200
    COMMENT_NOT_FOUND = 1201
    USER_NOT_FOUND_BY_ID = 1202
    
    # Database Errors (1300-1399)
    DATABASE_ERROR = 1300
    COMMIT_ERROR = 1301
    ROLLBACK_ERROR = 1302
    
    # File Upload Errors (1400-1499)
    FILE_TOO_LARGE = 1400
    INVALID_FILE_TYPE = 1401
    UPLOAD_FAILED = 1402
    
    # General Errors (1500-1599)
    INTERNAL_SERVER_ERROR = 1500
    BAD_REQUEST = 1501
    METHOD_NOT_ALLOWED = 1502

class ErrorMessages:
    """Error messages corresponding to error codes"""
    
    MESSAGES = {
        # Authentication Errors
        ErrorCodes.INVALID_CREDENTIALS: "Invalid username or password",
        ErrorCodes.USER_NOT_FOUND: "User not found",
        ErrorCodes.USERNAME_TAKEN: "Username already taken",
        ErrorCodes.EMAIL_TAKEN: "Email already registered",
        ErrorCodes.INVALID_TOKEN: "Invalid token",
        ErrorCodes.TOKEN_EXPIRED: "Token has expired",
        ErrorCodes.UNAUTHORIZED: "Unauthorized access",
        ErrorCodes.INVALID_REFRESH_TOKEN: "Invalid refresh token",
        
        # Validation Errors
        ErrorCodes.MISSING_REQUIRED_FIELDS: "Missing required fields",
        ErrorCodes.INVALID_USERNAME_LENGTH: "Username must be between 3 and 20 characters",
        ErrorCodes.INVALID_PASSWORD_LENGTH: "Password must be at least 6 characters",
        ErrorCodes.INVALID_EMAIL_FORMAT: "Invalid email format",
        ErrorCodes.INVALID_POST_TITLE_LENGTH: "Post title must be between 1 and 200 characters",
        ErrorCodes.INVALID_POST_CONTENT_LENGTH: "Post content must be between 1 and 10000 characters",
        ErrorCodes.INVALID_COMMENT_LENGTH: "Comment must be between 1 and 1000 characters",
        
        # Resource Errors
        ErrorCodes.POST_NOT_FOUND: "Post not found",
        ErrorCodes.COMMENT_NOT_FOUND: "Comment not found",
        ErrorCodes.USER_NOT_FOUND_BY_ID: "User not found with the provided ID",
        
        # Database Errors
        ErrorCodes.DATABASE_ERROR: "Database error occurred",
        ErrorCodes.COMMIT_ERROR: "Failed to save data",
        ErrorCodes.ROLLBACK_ERROR: "Failed to rollback transaction",
        
        # File Upload Errors
        ErrorCodes.FILE_TOO_LARGE: "File size exceeds maximum limit",
        ErrorCodes.INVALID_FILE_TYPE: "Invalid file type",
        ErrorCodes.UPLOAD_FAILED: "File upload failed",
        
        # General Errors
        ErrorCodes.INTERNAL_SERVER_ERROR: "Internal server error",
        ErrorCodes.BAD_REQUEST: "Bad request",
        ErrorCodes.METHOD_NOT_ALLOWED: "Method not allowed",
    }
    
    @classmethod
    def get_message(cls, error_code):
        """Get error message for a given error code"""
        return cls.MESSAGES.get(error_code, "Unknown error")
    
    @classmethod
    def get_error_response(cls, error_code, details=None):
        """Get standardized error response"""
        response = {
            "error": cls.get_message(error_code),
            "error_code": error_code
        }
        if details:
            response["details"] = details
        return response
