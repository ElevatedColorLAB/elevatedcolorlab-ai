<?php
// sales_auth.php
ini_set('display_errors', 1);
error_reporting(E_ALL);
session_start();

// USE THE MASTER CONNECTION FILE
require_once 'db_connect.php';

function send_json($data) {
    header('Content-Type: application/json');
    echo json_encode($data);
    exit();
}

$action = $_GET['action'] ?? '';

try {
    if ($action === 'register') {
        $username = $_POST['username'] ?? '';
        $password = $_POST['password'] ?? '';
        
        if (empty($username) || empty($password)) throw new Exception('Username and password required.');
        
        $stmt = $conn->prepare("SELECT id FROM sales_users WHERE username = ?");
        $stmt->bind_param("s", $username);
        $stmt->execute();
        if ($stmt->get_result()->num_rows > 0) throw new Exception('Username already exists.');
        $stmt->close();

        $hashed = password_hash($password, PASSWORD_DEFAULT);
        $stmt = $conn->prepare("INSERT INTO sales_users (username, password) VALUES (?, ?)");
        $stmt->bind_param("ss", $username, $hashed);
        $stmt->execute();
        
        send_json(['status' => 'success']);
    } 
    elseif ($action === 'login') {
        $username = $_POST['username'] ?? '';
        $password = $_POST['password'] ?? '';
        
        $stmt = $conn->prepare("SELECT id, username, password FROM sales_users WHERE username = ?");
        $stmt->bind_param("s", $username);
        $stmt->execute();
        $user = $stmt->get_result()->fetch_assoc();
        
        if ($user && password_verify($password, $user['password'])) {
            $_SESSION['sales_user_id'] = $user['id'];
            $_SESSION['sales_user_username'] = $user['username'];
            send_json(['status' => 'success', 'username' => $user['username']]);
        } else {
            throw new Exception('Invalid credentials.');
        }
    }
    elseif ($action === 'logout') {
        session_unset();
        session_destroy();
        // Redirect to the HTML login page
        header('Location: sales_login.html');
        exit();
    }
} catch (Exception $e) {
    http_response_code(400);
    send_json(['status' => 'error', 'message' => $e->getMessage()]);
}
?>