<?php
// main_auth.php
ini_set('display_errors', 1);
error_reporting(E_ALL);
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
session_start();
header('Content-Type: application/json');

// --- Self-Contained Database Connection ---
try {
    $servername = "db5018479985.hosting-data.io";
    $username = "dbu3256606";
    $password = "Elevated@Demonboy098!Logins";
    $dbname = "dbs14683606";
    $conn = new mysqli($servername, $username, $password, $dbname);
} catch (mysqli_sql_exception $e) {
    http_response_code(500);
    echo json_encode(['status' => 'error', 'message' => 'Database connection failed: ' . $e->getMessage()]);
    exit();
}

// --- Action Routing ---
$action = $_GET['action'] ?? '';
try {
    if ($action == 'register') {
        // Registration is disabled for pre-launch, but the code remains for the future.
        throw new Exception('Public registration is currently disabled.');
    } elseif ($action == 'login') {
        login_main_user($conn);
    } else {
        throw new Exception('Invalid action specified.');
    }
} catch (Exception $e) {
    http_response_code(400);
    echo json_encode(['status' => 'error', 'message' => $e->getMessage()]);
}

$conn->close();

/**
 * Handles login for main application users (Admin, Production Manager, etc.)
 */
function login_main_user($conn) {
    $username = $_POST['username'] ?? '';
    $password = $_POST['password'] ?? '';
    if (empty($username) || empty($password)) {
        throw new Exception('Username and password are required.');
    }

    $stmt = $conn->prepare("SELECT id, username, password, role FROM main_accounts WHERE username = ?");
    $stmt->bind_param("s", $username);
    $stmt->execute();
    $result = $stmt->get_result();
    $user = $result->fetch_assoc();
    $stmt->close();

    if ($user && password_verify($password, $user['password'])) {
        // Regenerate session ID for security
        session_regenerate_id(true);

        $token = bin2hex(random_bytes(16)); // Create a secure token for the session
        $_SESSION['main_user_id'] = $user['id'];
        $_SESSION['main_user_username'] = $user['username'];
        $_SESSION['main_user_role'] = $user['role'];
        $_SESSION['main_user_token'] = $token;

        echo json_encode([
            'status' => 'success', 
            'username' => $user['username'], 
            'role' => $user['role'],
            'token' => $token
        ]);
    } else {
        // Use a generic error message to prevent username enumeration
        throw new Exception('Invalid username or password.');
    }
}
?>