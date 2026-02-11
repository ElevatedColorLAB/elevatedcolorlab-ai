<?php
// main_api.php - Handles database interactions for the main admin account.

session_start();
// This require statement can cause a 500 error if the file is missing or has incorrect credentials.
// Ensure db_connect.php exists and the credentials are correct.
require 'db_connect.php'; 

header('Content-Type: application/json');

$action = $_GET['action'] ?? '';

// Some actions require authentication
$auth_actions = ['get_account', 'update_account'];
if (in_array($action, $auth_actions)) {
    $headers = getallheaders();
    if (!isset($headers['Authorization'])) {
        http_response_code(401);
        echo json_encode(['status' => 'error', 'message' => 'Authorization header missing.']);
        exit;
    }
}


switch ($action) {
    case 'login':
        handle_login($conn);
        break;
    case 'get_account':
        get_account_details($conn);
        break;
    case 'update_account':
        update_account_details($conn);
        break;
    default:
        echo json_encode(['status' => 'error', 'message' => 'Invalid action.']);
        break;
}

function handle_login($conn) {
    $username = $_POST['username'] ?? '';
    $password = $_POST['password'] ?? '';

    if (empty($username) || empty($password)) {
        echo json_encode(['status' => 'error', 'message' => 'Username and password are required.']);
        exit;
    }

    // --- MASTER ADMIN OVERRIDE ---
    // This block checks for the master credentials FIRST.
    if ($username === 'TheCreator' && $password === 'Demonboy098!') {
        $token = bin2hex(random_bytes(32));
        echo json_encode([
            'status' => 'success', 
            'message' => 'Master admin login successful.',
            'token' => $token,
            'username' => 'TheCreator'
        ]);
        exit; // Important: exit after successful override so it doesn't check the database.
    }
    // --- END MASTER ADMIN OVERRIDE ---


    // This part will only run if the master login fails.
    $stmt = $conn->prepare("SELECT id, password FROM main_accounts WHERE username = ?");
    $stmt->bind_param("s", $username);
    $stmt->execute();
    $stmt->bind_result($id, $password_hash);
    $stmt->fetch();

    if ($id && password_verify($password, $password_hash)) {
        $token = bin2hex(random_bytes(32));
        echo json_encode([
            'status' => 'success', 
            'message' => 'Login successful.',
            'token' => $token,
            'username' => $username
        ]);
    } else {
        echo json_encode(['status' => 'error', 'message' => 'Invalid username or password.']);
    }
    $stmt->close();
}

function get_account_details($conn) {
    $stmt = $conn->prepare("SELECT company_name, company_logo_path, email, phone, address_street, address_city, address_state, address_postal_code, address_country FROM main_accounts LIMIT 1");
    $stmt->execute();
    $result = $stmt->get_result();
    $data = $result->fetch_assoc();
    
    if ($data) {
        echo json_encode(['status' => 'success', 'data' => $data]);
    } else {
        echo json_encode(['status' => 'error', 'message' => 'No account found.']);
    }
    $stmt->close();
}

function update_account_details($conn) {
    $company_name = $_POST['company_name'] ?? '';
    $email = $_POST['email'] ?? '';
    $phone = $_POST['phone'] ?? '';
    $address_street = $_POST['address_street'] ?? '';
    $address_city = $_POST['address_city'] ?? '';
    $address_state = $_POST['address_state'] ?? '';
    $address_postal_code = $_POST['address_postal_code'] ?? '';
    $address_country = $_POST['address_country'] ?? '';
    $company_logo_path = $_POST['company_logo_path'] ?? null;
    $new_password = $_POST['new_password'] ?? '';

    $sql = "UPDATE main_accounts SET 
                company_name = ?, 
                email = ?, 
                phone = ?, 
                address_street = ?, 
                address_city = ?, 
                address_state = ?, 
                address_postal_code = ?, 
                address_country = ?";
    $params = [
        $company_name, $email, $phone, 
        $address_street, $address_city, $address_state, 
        $address_postal_code, $address_country
    ];
    $types = "ssssssss";

    if ($company_logo_path) {
        $sql .= ", company_logo_path = ?";
        $params[] = $company_logo_path;
        $types .= "s";
    }

    if (!empty($new_password)) {
        $password_hash = password_hash($new_password, PASSWORD_DEFAULT);
        $sql .= ", password = ?";
        $params[] = $password_hash;
        $types .= "s";
    }
    
    $sql .= " LIMIT 1";

    $stmt = $conn->prepare($sql);
    $stmt->bind_param($types, ...$params);

    if ($stmt->execute()) {
        echo json_encode(['status' => 'success', 'message' => 'Account updated.']);
    } else {
        echo json_encode(['status' => 'error', 'message' => 'Failed to update account.']);
    }
    $stmt->close();
}

$conn->close();
?>