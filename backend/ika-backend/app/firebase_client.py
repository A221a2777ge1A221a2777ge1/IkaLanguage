"""
Firebase Admin SDK Client Initialization
Uses Application Default Credentials (ADC) on Cloud Run / Cloud Shell
"""
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import storage as gcs_storage
import logging

logger = logging.getLogger(__name__)

_firebase_app = None
_firestore_client = None
_storage_clients = {}


def get_firestore_client(project_id: str):
    """
    Initialize and return Firestore client using Application Default Credentials.
    Idempotent - safe to call multiple times.
    """
    global _firebase_app, _firestore_client
    
    if _firestore_client is not None:
        return _firestore_client
    
    try:
        # Initialize Firebase Admin SDK if not already initialized
        if _firebase_app is None:
            # Use Application Default Credentials
            # In Cloud Run, this automatically uses the service account
            cred = credentials.ApplicationDefault()
            _firebase_app = firebase_admin.initialize_app(
                cred,
                options={'projectId': project_id}
            )
            logger.info(f"Firebase Admin SDK initialized for project: {project_id}")
        
        _firestore_client = firestore.client()
        logger.info("Firestore client initialized")
        return _firestore_client
        
    except Exception as e:
        logger.error(f"Failed to initialize Firestore client: {str(e)}", exc_info=True)
        raise


def get_storage_client(project_id: str, bucket_name: str):
    """
    Initialize and return Google Cloud Storage client.
    Idempotent - safe to call multiple times.
    """
    global _storage_clients
    
    if bucket_name in _storage_clients:
        return _storage_clients[bucket_name]
    
    try:
        # Use Application Default Credentials
        storage_client = gcs_storage.Client(project=project_id)
        _storage_clients[bucket_name] = storage_client
        logger.info(f"Storage client initialized for bucket: {bucket_name}")
        return storage_client
        
    except Exception as e:
        logger.error(f"Failed to initialize Storage client: {str(e)}", exc_info=True)
        raise
