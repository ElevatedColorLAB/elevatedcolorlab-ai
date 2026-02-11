<?php
// --- Error Handling ---
ini_set('display_errors', 0);
error_reporting(E_ALL);

register_shutdown_function(function () {
    $error = error_get_last();
    if ($error !== null && in_array($error['type'], [E_ERROR, E_CORE_ERROR, E_COMPILE_ERROR, E_USER_ERROR])) {
        if (ob_get_length()) ob_end_clean();
        header('Content-Type: application/json');
        http_response_code(500);
        echo json_encode([
            'status' => 'error',
            'message' => 'A critical server error occurred.',
            'details' => $error['message']
        ]);
        exit();
    }
});

ob_start();

function send_json($data) {
    if (ob_get_length()) ob_end_clean();
    header('Content-Type: application/json');
    echo json_encode($data);
    exit();
}

session_start();

// --- Supabase Config ---
$SUPABASE_URL = 'https://egbvlbqjlrvmtnbetxmy.supabase.co';
$SUPABASE_KEY = ' ';

$REST_URL = $SUPABASE_URL . '/rest/v1';
$STORAGE_URL = $SUPABASE_URL . '/storage/v1/object';

// --- Route ---
$action = $_GET['action'] ?? '';

switch ($action) {
    case 'submit_request':
        submit_request($SUPABASE_URL, $SUPABASE_KEY);
        break;

    case 'get_requests':
        get_requests($REST_URL, $SUPABASE_KEY);
        break;

    case 'get_archived_requests':
        get_archived_requests($REST_URL, $SUPABASE_KEY);
        break;

    default:
        send_json(['status' => 'error', 'message' => 'Invalid API action']);
}

// --- FUNCTIONS ---

function submit_request($SUPABASE_URL, $SUPABASE_KEY) {
    $STORAGE_URL = $SUPABASE_URL . '/storage/v1/object';
    $REST_URL = $SUPABASE_URL . '/rest/v1';

    // Upload file if provided
    $file_url = null;
    if (!empty($_FILES['artwork_file']['tmp_name'])) {
        $bucket = 'artwork_files';
        $filename = uniqid() . '_' . basename($_FILES['artwork_file']['name']);
        $filepath = $_FILES['artwork_file']['tmp_name'];

        $ch = curl_init("$STORAGE_URL/$bucket/$filename");
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST => true,
            CURLOPT_HTTPHEADER => [
                "Authorization: Bearer $SUPABASE_KEY",
                "Content-Type: " . $_FILES['artwork_file']['type']
            ],
            CURLOPT_POSTFIELDS => file_get_contents($filepath)
        ]);

        $response = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($code === 200 || $code === 201) {
            $file_url = "$SUPABASE_URL/storage/v1/object/public/$bucket/$filename";
        }
    }

    // Build request data
    $data = [
        'customer_name' => $_POST['customer_name'],
        'po_number' => $_POST['po_number'] ?? null,
        'due_date' => $_POST['due_date'],
        'product_type' => $_POST['product_type'],
        'image_placement' => $_POST['image_placement'],
        'process_type' => $_POST['process_type'],
        'request_type' => $_POST['request_type'],
        'details' => $_POST['details'],
        'uploaded_files' => $file_url ? [$file_url] : [],
        'salesperson_name' => $_SESSION['sales_user_username'],
        'salesperson_id' => $_SESSION['sales_user_id'],
        'status' => 'New',
        'approval_status' => 'Pending',
        'priority_level' => 'Normal',
        'is_archived' => false
    ];

    // Insert into Supabase
    $ch = curl_init("$REST_URL/art_requests");
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST => true,
        CURLOPT_HTTPHEADER => [
            "apikey: $SUPABASE_KEY",
            "Authorization: Bearer $SUPABASE_KEY",
            "Content-Type: application/json"
        ],
        CURLOPT_POSTFIELDS => json_encode([$data])
    ]);

    $response = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($code === 201) {
        send_json(['status' => 'success']);
    } else {
        send_json(['status' => 'error', 'message' => 'Failed to submit request']);
    }
}

function get_requests($REST_URL, $SUPABASE_KEY) {
    $url = "$REST_URL/art_requests?is_archived=eq.false&order=created_at.desc";

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => [
            "apikey: $SUPABASE_KEY",
            "Authorization: Bearer $SUPABASE_KEY"
        ]
    ]);

    $response = curl_exec($ch);
    curl_close($ch);

    send_json(['status' => 'success', 'data' => json_decode($response, true)]);
}

function get_archived_requests($REST_URL, $SUPABASE_KEY) {
    $url = "$REST_URL/art_requests?is_archived=eq.true&order=created_at.desc";

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => [
            "apikey: $SUPABASE_KEY",
            "Authorization: Bearer $SUPABASE_KEY"
        ]
    ]);

    $response = curl_exec($ch);
    curl_close($ch);

    send_json(['status' => 'success', 'data' => json_decode($response, true)]);
}
?>