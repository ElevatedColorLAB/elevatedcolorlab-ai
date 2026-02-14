<?php
// upload.php - Handles file uploads AND creates the art request in the database.

session_start();
require 'db_connect.php';

header('Content-Type: application/json');

// --- Authentication Check ---
// Ensure a salesperson is logged in to submit a request.
if (!isset($_SESSION['sales_user_id'])) {
    http_response_code(401);
    echo json_encode(['status' => 'error', 'message' => 'Unauthorized: You must be logged in to submit a request.']);
    exit;
}
$sales_user_id = $_SESSION['sales_user_id'];

// --- Validation ---
// Check if file was uploaded without errors
if (!isset($_FILES['artworkFile']) || $_FILES['artworkFile']['error'] != 0) {
    http_response_code(400);
    echo json_encode(['status' => 'error', 'message' => 'No file was uploaded or an error occurred during upload.']);
    exit;
}

// Check for required POST fields
$required_fields = ['customer_name', 'request_type', 'details', 'product_type', 'image_placement', 'process_type'];
foreach ($required_fields as $field) {
    if (empty($_POST[$field])) {
        http_response_code(400);
        echo json_encode(['status' => 'error', 'message' => "Missing required field: $field"]);
        exit;
    }
}

// --- File Handling ---
$customer_name_sanitized = preg_replace('/[^a-zA-Z0-9_\-]/', '_', $_POST['customer_name']);
$upload_dir = 'uploads/' . $customer_name_sanitized . '/';

// Create customer-specific directory if it doesn't exist
if (!is_dir($upload_dir)) {
    if (!mkdir($upload_dir, 0777, true)) {
        http_response_code(500);
        echo json_encode(['status' => 'error', 'message' => 'Failed to create upload directory. Check server permissions.']);
        exit;
    }
}

$file_name = basename($_FILES['artworkFile']['name']);
$file_extension = pathinfo($file_name, PATHINFO_EXTENSION);
$unique_file_name = uniqid() . '_' . time() . '.' . $file_extension;
$target_file_path = $upload_dir . $unique_file_name;

// Move the uploaded file to the target directory
if (!move_uploaded_file($_FILES['artworkFile']['tmp_name'], $target_file_path)) {
    http_response_code(500);
    echo json_encode(['status' => 'error', 'message' => 'Failed to move uploaded file.']);
    exit;
}


// --- Database Insertion ---
try {
    $stmt = $conn->prepare(
        "INSERT INTO art_requests (sales_user_id, customer_name, po_number, due_date, product_type, image_placement, process_type, request_type, details, artwork_path) 
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    );

    // Bind parameters from the POST data
    $stmt->bind_param(
        "isssssssss",
        $sales_user_id,
        $_POST['customer_name'],
        $_POST['po_number'],
        $_POST['due_date'],
        $_POST['product_type'],
        $_POST['image_placement'],
        $_POST['process_type'],
        $_POST['request_type'],
        $_POST['details'],
        $target_file_path
    );

    if ($stmt->execute()) {
        echo json_encode(['status' => 'success', 'message' => 'Art request submitted successfully!']);
    } else {
        // If execute fails, throw an exception to be caught below
        throw new Exception("Database insertion failed: " . $stmt->error);
    }
    $stmt->close();
    
} catch (Exception $e) {
    // If the database insert fails, try to delete the orphaned file
    if (file_exists($target_file_path)) {
        unlink($target_file_path);
    }
    http_response_code(500);
    echo json_encode(['status' => 'error', 'message' => $e->getMessage()]);
}

$conn->close();
?>
