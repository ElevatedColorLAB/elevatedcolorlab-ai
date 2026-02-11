<?php
// update_request.php - Updates the status and adds responses to a request.

header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['status' => 'error', 'message' => 'Only POST requests are accepted.']);
    exit;
}

$json_data = file_get_contents('php://input');
$data = json_decode($json_data, true);

if (!isset($data['id'], $data['folder'], $data['status'], $data['response'])) {
    http_response_code(400);
    echo json_encode(['status' => 'error', 'message' => 'Missing required parameters.']);
    exit;
}

$request_id = $data['id'];
$folder = $data['folder'];
$new_status = $data['status'];
$new_response = $data['response'];

$status_file = 'uploads/' . basename($folder) . '/' . basename($request_id) . '_status.json';

if (!file_exists($status_file)) {
    http_response_code(404);
    echo json_encode(['status' => 'error', 'message' => 'Status file not found.']);
    exit;
}

$status_data = json_decode(file_get_contents($status_file), true);

// Update status
$status_data['status'] = $new_status;

// Add new response if it's not empty
if (!empty(trim($new_response))) {
    $status_data['responses'][] = [
        'user' => 'Art Department', // Or get from a session
        'timestamp' => date('Y-m-d H:i:s'),
        'message' => $new_response
    ];
}

// Save the updated data
if (file_put_contents($status_file, json_encode($status_data, JSON_PRETTY_PRINT))) {
    echo json_encode(['status' => 'success', 'message' => 'Request updated successfully.']);
} else {
    http_response_code(500);
    echo json_encode(['status' => 'error', 'message' => 'Failed to write to status file.']);
}
?>
