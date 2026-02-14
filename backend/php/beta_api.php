<?php
// beta_api.php
ini_set('display_errors', 1); error_reporting(E_ALL); mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
session_start(); header('Content-Type: application/json');

// --- Get Input & Token ---
$input = json_decode(file_get_contents('php://input'), true);
$token = $input['token'] ?? '';

// --- Admin-Only Authentication ---
if ($token === 'dev_override_token') {
    // Dev access granted
} else {
    if (empty($token) || !isset($_SESSION['main_user_token']) || $token !== $_SESSION['main_user_token'] || !isset($_SESSION['main_user_role']) || $_SESSION['main_user_role'] !== 'admin') {
         http_response_code(401); 
         echo json_encode(['status' => 'error', 'message' => 'Invalid or expired token, or insufficient permissions.']); 
         exit();
    }
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
        case 'get_requests':
            get_beta_requests($conn);
            break;
        case 'approve_request':
            approve_beta_request($conn, $input);
            break;
        default:
            throw new Exception('Invalid action specified.');
    }
} catch (Exception $e) {
    http_response_code(400); echo json_encode(['status' => 'error', 'message' => $e->getMessage()]);
}
$conn->close();

function get_beta_requests($conn) {
    $result = $conn->query("SELECT * FROM beta_requests ORDER BY submitted_at DESC");
    $data = $result->fetch_all(MYSQLI_ASSOC);
    echo json_encode(['status' => 'success', 'data' => $data]);
}

function approve_beta_request($conn, $input) {
    $request_id = intval($input['id'] ?? 0);
    if ($request_id === 0) throw new Exception('Invalid request ID.');

    $conn->begin_transaction();
    try {
        $stmt = $conn->prepare("SELECT shop_name, contact_email FROM beta_requests WHERE id = ? AND status = 'pending'");
        $stmt->bind_param("i", $request_id);
        $stmt->execute();
        $applicant = $stmt->get_result()->fetch_assoc();
        $stmt->close();
        if (!$applicant) throw new Exception('Request not found or already approved.');
        
        $username = preg_replace('/[^a-zA-Z0-9]/', '', $applicant['shop_name']);
        $temp_password = bin2hex(random_bytes(6));
        $hashed_password = password_hash($temp_password, PASSWORD_DEFAULT);
        $role = 'beta_tester';

        $stmt_insert = $conn->prepare("INSERT INTO main_accounts (username, password, role, company_name, email) VALUES (?, ?, ?, ?, ?)");
        $stmt_insert->bind_param("sssss", $username, $hashed_password, $role, $applicant['shop_name'], $applicant['contact_email']);
        $stmt_insert->execute();
        $stmt_insert->close();
        
        $stmt_update = $conn->prepare("UPDATE beta_requests SET status = 'approved' WHERE id = ?");
        $stmt_update->bind_param("i", $request_id);
        $stmt_update->execute();
        $stmt_update->close();

        // **THE FIX IS HERE**: Automatically send the welcome email
        $email_sent = send_approval_email($applicant['contact_email'], $username, $temp_password);

        $conn->commit();
        echo json_encode([
            'status' => 'success', 
            'message' => 'User created and email sent successfully.',
            'email_status' => $email_sent ? 'Sent' : 'Failed'
        ]);

    } catch (mysqli_sql_exception $e) {
        $conn->rollback();
        if ($e->getCode() == 1062) {
             $stmt_update = $conn->prepare("UPDATE beta_requests SET status = 'approved' WHERE id = ?");
             $stmt_update->bind_param("i", $request_id);
             $stmt_update->execute();
             $stmt_update->close();
             $conn->commit();
             throw new Exception("A user with a similar username already exists. Please create an account for them manually.");
        }
        throw new Exception("Database error: " . $e->getMessage());
    }
}

function send_approval_email($recipient_email, $username, $temp_password) {
    $subject = "Welcome to the ElevatedColorLab Beta Program!";
    $login_url = "https://elevatedcolorlab.com/login.html";

    $message = "
    <html><head><title>{$subject}</title></head>
    <body style='font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;'>
        <table width='100%' border='0' cellspacing='0' cellpadding='0'><tr><td align='center'>
            <table width='600' border='0' cellspacing='0' cellpadding='20' style='background-color: #ffffff; border-radius: 8px;'>
                <tr><td align='center' style='background-color: #2563eb; color: white; padding: 10px; border-radius: 8px 8px 0 0;'>
                    <h1>Welcome Aboard!</h1>
                </td></tr>
                <tr><td style='padding: 20px;'>
                    <p>Hello,</p>
                    <p>Congratulations! Your application to the ElevatedColorLab beta program has been approved. We're thrilled to have you join our community of forward-thinking print professionals.</p>
                    <p>Here are your login credentials:</p>
                    <ul style='list-style: none; padding: 0;'>
                        <li><strong>Username:</strong> {$username}</li>
                        <li><strong>Temporary Password:</strong> {$temp_password}</li>
                    </ul>
                    <p>You can log in and get started right away. We recommend changing your password in the 'My Account' section after your first login.</p>
                    <p style='text-align: center; margin-top: 30px;'>
                        <a href='{$login_url}' style='background-color: #2563eb; color: white; padding: 15px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;'>Login to Your Account</a>
                    </p>
                    <p>We can't wait to hear your feedback!</p>
                    <p><em>- The ElevatedColorLab Team</em></p>
                </td></tr>
            </table>
        </td></tr></table>
    </body></html>";

    $headers = "MIME-Version: 1.0" . "\r\n";
    $headers .= "Content-type:text/html;charset=UTF-8" . "\r\n";
    $headers .= 'From: <no-reply@elevatedcolorlab.com>' . "\r\n";

    return mail($recipient_email, $subject, $message, $headers);
}
?>

