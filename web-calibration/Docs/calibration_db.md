classDiagram
direction BT
class api_access_tokens {
   varchar(64) token_hash
   varchar(100) system_name
   json permissions
   tinyint(1) is_active
   timestamp created_at
   timestamp expires_at
   timestamp last_used_at
   int id
}
class calibration_audit_log {
   varchar(255) candidate_id
   varchar(50) action
   varchar(255) user_agent
   varchar(45) ip_address
   json details
   timestamp created_at
   int id
}
class calibration_data {
   varchar(255) candidate_id
   longtext calibration_csv  /* CSV data for calibration points */
   longblob transform_matrix_data  /* NPZ file data as binary */
   timestamp created_at
   timestamp updated_at
   varchar(64) file_checksum  /* SHA256 checksum for data validation */
   int id
}
class calibration_frames {
   varchar(36) session_id
   int frame_index
   json frame_data  /* Frame metadata and gaze data */
   json target_position  /* Target position for this frame */
   timestamp created_at
   int id
}
class calibration_sessions {
   varchar(255) candidate_id
   timestamp created_at
   timestamp updated_at
   enum('in_progress', 'completed', 'failed') status
   varchar(255) interview_id
   text error_message
   json metadata
   varchar(36) id
}
class screen_info {
   varchar(255) candidate_id
   json screen_data  /* Stores complete screen configuration */
   timestamp created_at
   timestamp updated_at
   int id
}

calibration_frames  -->  calibration_sessions : session_id:id
