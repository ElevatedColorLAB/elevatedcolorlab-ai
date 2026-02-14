<?php
// team_api.php
ini_set('display_errors', 1); error_reporting(E_ALL); mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
session_start(); header('Content-Type: application/json');

// --- Get Input & Token ---
$input = json_decode(file_get_contents('php://input'), true);
$token = $input['token'] ?? '';
$main_account_id = null;

// --- Authentication & Account ID Retrieval ---
if ($token === 'dev_override_token') {
    $main_account_id = 1; // Dev override uses Account ID 1
} else {
    if (empty($token) || !isset($_SESSION['main_user_token']) || $token !== $_SESSION['main_user_token']) {
         http_response_code(401); echo json_encode(['status' => 'error', 'message' => 'Invalid or expired token.']); exit();
    }
    $main_account_id = $_SESSION['main_user_id'];
}

// --- Database Connection ---
try {
    $servername = "db5018479985.hosting-data.io"; $username = "dbu3256606";
    $password = "Elevated@Demonboy098!Logins"; $dbname = "dbs14683606";
    $conn = new mysqli($servername, $username, $password, $dbname);
} catch (mysqli_sql_exception $e) {
    http_response_code(500); echo json_encode(['status' => 'error', 'message' => 'Database connection failed.']); exit();
}

$action = $_GET['action'] ?? '';
try {
    switch($action) {
        case 'get_team':
            get_sales_team($conn, $main_account_id);
            break;
        case 'add_salesperson':
            add_salesperson($conn, $main_account_id, $input);
            break;
        default:
            throw new Exception('Invalid action specified.');
    }
} catch (Exception $e) {
    http_response_code(400); echo json_encode(['status' => 'error', 'message' => $e->getMessage()]);
}
$conn->close();

function get_sales_team($conn, $main_account_id) {
    $stmt = $conn->prepare("SELECT id, username, created_at FROM sales_users WHERE main_account_id = ? ORDER BY username");
    $stmt->bind_param("i", $main_account_id);
    $stmt->execute();
    $data = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
    $stmt->close();
    echo json_encode(['status' => 'success', 'data' => $data]);
}

function add_salesperson($conn, $main_account_id, $input) {
    $username = $input['username'] ?? '';
    $password = $input['password'] ?? '';
    if (empty($username) || empty($password)) throw new Exception('Username and password are required.');
    
    $hashed_password = password_hash($password, PASSWORD_DEFAULT);
    
    try {
        $stmt = $conn->prepare("INSERT INTO sales_users (main_account_id, username, password) VALUES (?, ?, ?)");
        $stmt->bind_param("iss", $main_account_id, $username, $hashed_password);
        $stmt->execute();
        $stmt->close();
        echo json_encode(['status' => 'success']);
    } catch (mysqli_sql_exception $e) {
        if ($e->getCode() == 1062) { // Duplicate entry
            throw new Exception('A salesperson with this username already exists.');
        }
        throw new Exception('Database error: ' . $e->getMessage());
    }
}
?>
