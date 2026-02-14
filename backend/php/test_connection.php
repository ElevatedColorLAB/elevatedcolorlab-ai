<?php
// --- Enhanced Error Reporting for Debugging ---
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

// Set the content type to plain text to see errors clearly
header('Content-Type: text/plain');

echo "Attempting to connect to the database...\n\n";

// --- Database Connection ---
// This uses the exact same method as your working inventory script.
// If this fails, the problem is with the file path or server configuration.
try {
    require 'db_connect.php';
    echo "Successfully included db_connect.php.\n";
} catch (Throwable $t) {
    echo "FATAL ERROR: Could not include 'db_connect.php'. Please check the file path.\n";
    echo "Error details: " . $t->getMessage();
    exit();
}


// Check for connection errors
if ($conn->connect_error) {
    echo "FATAL ERROR: Database connection failed: " . $conn->connect_error;
    exit();
}

echo "Database connection successful.\n\n";
echo "Attempting to fetch data from 'art_requests' table...\n\n";

// --- Fetch Data ---
$sql = "SELECT id, customer_name, request_type, po_number, created_at, status FROM art_requests ORDER BY created_at DESC";
$result = $conn->query($sql);

if ($result) {
    if ($result->num_rows > 0) {
        echo "SUCCESS: Found " . $result->num_rows . " art requests.\n\n";
        $requests = [];
        while ($row = $result->fetch_assoc()) {
            $requests[] = $row;
        }
        // Print the data in a readable format
        print_r($requests);
    } else {
        echo "QUERY SUCCESSFUL, BUT... no art requests were found in the table.\n";
        echo "This means the connection and query are working, but the table is empty for this user.";
    }
} else {
    echo "FATAL ERROR: Failed to execute query.\n";
    echo "Database error message: " . $conn->error;
}

// Close the database connection
$conn->close();

?>
