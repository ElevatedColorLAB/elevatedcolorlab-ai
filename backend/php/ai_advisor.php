<?php
// ai_advisor.php
// Backend for the AI Advisor modal (DeepSeek R1)

header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Headers: Content-Type");
header("Content-Type: application/json");

// 1. Read JSON body
$raw = file_get_contents("php://input");
$data = json_decode($raw, true);

if (!$data || empty($data['context'])) {
    http_response_code(400);
    echo json_encode(["error" => "Missing 'context' in request body"]);
    exit;
}

$context = $data['context'];

// 2. DeepSeek API config
$api_key = "xxxxxxxxxxxxxxxxxxxxxxxxxxx"; // <-- REPLACE THIS AFTER REGENERATING
$endpoint = "https://api.deepseek.com/chat/completions";

// 3. Build payload for DeepSeek R1 (reasoning model)
$payload = [
    "model" => "deepseek-reasoner", // R1 reasoning model name
    "temperature" => 0.2,
    "max_tokens" => 800,
    "messages" => [
        [
            "role" => "system",
            "content" => "You are an expert print production advisor for apparel. 
You analyze design metadata (resolution, colors, transparency, style hints) and recommend the best decoration method 
(screen printing, DTF, embroidery, etc.) and which tools to run (upscaler, background remover, vectorizer, knockout, halftone, digitizer). 
Be concrete and practical, avoid hallucinating, and if something is uncertain, say so."
        ],
        [
            "role" => "user",
            "content" => $context
        ]
    ]
];

$ch = curl_init($endpoint);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    "Content-Type: application/json",
    "Authorization: Bearer " . $api_key
]);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));

// 4. Call DeepSeek
$response = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);

if (curl_errno($ch)) {
    http_response_code(502);
    echo json_encode([
        "error" => "DeepSeek API call failed",
        "curl_error" => curl_error($ch)
    ]);
    curl_close($ch);
    exit;
}

curl_close($ch);

// 5. Pass DeepSeek's response through to frontend
http_response_code($http_code);
echo $response;
