<?php
// db_connect.php
// Single source of truth for database connection

ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

$db_host = "db5018479985.hosting-data.io";
$db_user = "dbu3256606";
$db_pass = "Elevated@Demonboy098!Logins";
$db_name = "dbs14683606";

try {
    $conn = new mysqli($db_host, $db_user, $db_pass, $db_name);
    if ($conn->connect_error) {
        throw new Exception("Connection failed: " . $conn->connect_error);
    }
} catch (Exception $e) {
    header('Content-Type: application/json');
    http_response_code(500);
    echo json_encode(['status' => 'error', 'message' => 'Database connection error.']);
    exit();
}
?>