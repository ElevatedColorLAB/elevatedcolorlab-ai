<?php
// --- STEP 1: Enhanced Error Reporting ---
// Force PHP to display any and all errors.
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

// --- STEP 2: Self-Contained Database Connection ---
// This removes the dependency on an external file.
$servername = "db5018479985.hosting-data.io";
$username = "dbu3256606";
$password = "Elevated@Demonboy098!Logins";
$dbname = "dbs14683606";

// Set the content type to JSON for the final response
header('Content-Type: application/json');

// Create connection
$conn = new mysqli($servername, $username, $password, $dbname);

// Check connection
if ($conn->connect_error) {
    echo json_encode(['status' => 'error', 'message' => 'FATAL: Database Connection Failed: ' . $conn->connect_error]);
    exit();
}

// --- STEP 3: Detailed File Upload Check ---
// Check if the file array exists and if there's an error code.
if (!isset($_FILES['artwork_file']) || !is_uploaded_file($_FILES['artwork_file']['tmp_name'])) {
    $errorCode = $_FILES['artwork_file']['error'] ?? 'UNKNOWN';
    echo json_encode(['status' => 'error', 'message' => "SERVER ERROR: No file was uploaded. PHP error code: " . $errorCode . ". This is likely a server configuration issue (upload_max_filesize)."]);
    exit();
}

// --- STEP 4: Directory and Permissions Check ---
$upload_dir = 'customer_uploads/';
$customer_name_sanitized = preg_replace("/[^a-zA-Z0-9_]/", "", strtolower($_POST['customer_name']));
$customer_folder = $upload_dir . $customer_name_sanitized;

// Check if the base upload directory exists.
if (!is_dir($upload_dir)) {
    echo json_encode(['status' => 'error', 'message' => "SERVER PERMISSION ERROR: The base directory '{$upload_dir}' does not exist. Please create it."]);
    exit();
}
// Check if the base upload directory is writable.
if (!is_writable($upload_dir)) {
    echo json_encode(['status' => 'error', 'message' => "SERVER PERMISSION ERROR: The base directory '{$upload_dir}' is not writable. Please check folder permissions (set to 755 or 777)."]);
    exit();
}

// Create the customer-specific folder if it doesn't exist.
if (!is_dir($customer_folder)) {
    if (!mkdir($customer_folder, 0777, true)) {
        echo json_encode(['status' => 'error', 'message' => "SERVER PERMISSION ERROR: Failed to create customer directory '{$customer_folder}'. Please check parent folder permissions."]);
        exit();
    }
}

// --- STEP 5: Move the File ---
$file_extension = pathinfo($_FILES['artwork_file']['name'], PATHINFO_EXTENSION);
$new_filename = uniqid('art_', true) . '.' . $file_extension;
$artwork_path = $customer_folder . '/' . $new_filename;

if (!move_uploaded_file($_FILES['artwork_file']['tmp_name'], $artwork_path)) {
    echo json_encode(['status' => 'error', 'message' => 'FATAL: move_uploaded_file() failed. Check final directory permissions.']);
    exit();
}

// --- STEP 6: Insert into Database ---
try {
    // sales_user_id is hardcoded to 1. In a real system, get this from a login session.
    $sales_user_id = 1; 

    $sql = "INSERT INTO art_requests (sales_user_id, customer_name, customer_email, po_number, due_date, product_type, image_placement, process_type, request_type, details, artwork_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
    
    $stmt = $conn->prepare($sql);
    
    $stmt->bind_param(
        "issssssssss",
        $sales_user_id,
        $_POST['customer_name'],
        $_POST['customer_email'],
        $_POST['po_number'],
        $_POST['due_date'],
        $_POST['product_type'],
        $_POST['image_placement'],
        $_POST['process_type'],
        $_POST['request_type'],
        $_POST['details'],
        $artwork_path
    );

    if ($stmt->execute()) {
        echo json_encode(['status' => 'success', 'message' => 'Request submitted successfully! The page will now refresh.']);
    } else {
        throw new Exception('Database execute failed: ' . $stmt->error);
    }
    $stmt->close();

} catch (Exception $e) {
    // If the database insert fails, delete the orphaned file.
    if (file_exists($artwork_path)) {
        unlink($artwork_path);
    }
    echo json_encode(['status' => 'error', 'message' => 'DATABASE ERROR: ' . $e->getMessage()]);
}

$conn->close();
?>
