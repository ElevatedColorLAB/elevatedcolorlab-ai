<?php
// api-proxy.php — Secure gateway to Python microservices

header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json");

// Debug mode toggle
$debug = false;

// Port map
$port_map = [
    'main_app'    => 8000,
    'upscaler'    => 8001,
    'vectorizer'  => 8002,
    'production'  => 8004,
    'bg_remover'  => 8005,
    'halftone'    => 8006,
    'digitizer'   => 8007,
    'image_prep'  => 8008
];

// Capture request
$service  = $_POST['service'] ?? $_GET['service'] ?? '';
$endpoint = $_POST['endpoint'] ?? $_GET['endpoint'] ?? '/';
$method   = $_POST['method'] ?? $_GET['method'] ?? 'POST';
$payload  = $_POST['payload'] ?? '{}';

// Validate service
if (!array_key_exists($service, $port_map)) {
    http_response_code(400);
    echo json_encode(["error" => "Invalid service: $service"]);
    exit;
}

$port = $port_map[$service];
$target_url = "http://127.0.0.1:$port$endpoint";

// Init cURL
$ch = curl_init($target_url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 300);

// Handle method
if ($method === 'POST') {
    curl_setopt($ch, CURLOPT_POST, 1);
    $json_data = json_decode($payload, true);

    if (!empty($_FILES['file'])) {
        $cfile = new CURLFile($_FILES['file']['tmp_name'], $_FILES['file']['type'], $_FILES['file']['name']);
        $post_data = ['file' => $cfile];
        if ($json_data) {
            foreach ($json_data as $key => $value) {
                $post_data[$key] = $value;
            }
        }
        curl_setopt($ch, CURLOPT_POSTFIELDS, $post_data);
    } else {
        curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
        curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    }
} elseif ($method === 'GET') {
    curl_setopt($ch, CURLOPT_HTTPGET, true);
}

// Execute
$response = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$content_type = curl_getinfo($ch, CURLINFO_CONTENT_TYPE);
curl_close($ch);

// Handle response
if ($response === false) {
    http_response_code(502);
    echo json_encode([
        "error" => "Backend unreachable",
        "curl_error" => curl_error($ch),
        "target_url" => $target_url
    ]);
} else {
    http_response_code($http_code);
    header("Content-Type: $content_type");
    echo $response;

    if ($debug) {
        error_log("Proxy to $target_url returned $http_code");
    }
}
?>