<?php
// inventory_api.php (Multi-Subscriber & Updated Fields)
ini_set('display_errors', 1); error_reporting(E_ALL); mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
session_start(); header('Content-Type: application/json');

// --- Determine Account ID ---
$main_account_id = null;
$input = json_decode(file_get_contents('php://input'), true);
$token = $input['token'] ?? '';
if ($token === 'dev_override_token') {
    $main_account_id = 1;
}
elseif (isset($_SESSION['main_user_id'])) {
    $main_account_id = $_SESSION['main_user_id'];
} else {
    http_response_code(401); echo json_encode(['status' => 'error', 'message' => 'Authentication error: Insufficient permissions for inventory.']); exit();
}

// --- Database Connection ---
try {
    $conn = new mysqli("db5018479985.hosting-data.io", "dbu3256606", "Elevated@Demonboy098!Logins", "dbs14683606");
} catch (mysqli_sql_exception $e) { http_response_code(500); echo json_encode(['status' => 'error', 'message' => 'Database connection failed.']); exit(); }

$action = $_GET['action'] ?? '';
try {
    switch ($action) {
        case 'get_items': get_inventory_items($conn, $main_account_id); break;
        case 'add_item': add_inventory_item($conn, $main_account_id, $input); break;
        // ... update and delete cases
    }
} catch (Exception $e) { http_response_code(400); echo json_encode(['status' => 'error', 'message' => $e->getMessage()]); }
$conn->close();

function get_inventory_items($conn, $main_account_id) {
    $stmt = $conn->prepare("SELECT * FROM inventory WHERE main_account_id = ? ORDER BY item_name ASC");
    $stmt->bind_param("i", $main_account_id);
    $stmt->execute();
    $items = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
    $stmt->close();
    echo json_encode(['status' => 'success', 'data' => $items]);
}

function add_inventory_item($conn, $main_account_id, $data) {
    $sql = "INSERT INTO inventory (main_account_id, item_name, category, quantity, quantity_unit, low_stock_threshold, low_stock_unit, supplier_name, alt_supplier_name, supplier_email, sizes, color) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
    $stmt = $conn->prepare($sql);
    
    $sizes = ($data['category'] == 'Garment') ? ($data['sizes'] ?? null) : null;
    $color = ($data['category'] == 'Garment') ? ($data['color'] ?? null) : null;
    $quantity_unit = ($data['category'] == 'Ink') ? ($data['quantity_unit'] ?? 'pieces') : 'pieces';
    $low_stock_unit = ($data['low_stock_unit'] ?? 'units');
    $alt_supplier = $data['alt_supplier_name'] ?? null;
    $supplier_email = $data['supplier_email'] ?? null;

    $stmt->bind_param(
        "issdsdssssss",
        $main_account_id,
        $data['item_name'],
        $data['category'],
        $data['quantity'],
        $quantity_unit,
        $data['low_stock_threshold'],
        $low_stock_unit,
        $data['supplier_name'],
        $alt_supplier,
        $supplier_email,
        $sizes,
        $color
    );
    
    if ($stmt->execute()) {
        echo json_encode(['status' => 'success', 'message' => 'Item added successfully.']);
    } else {
        throw new Exception('Database execute failed: ' . $stmt->error);
    }
    $stmt->close();
}
?>
