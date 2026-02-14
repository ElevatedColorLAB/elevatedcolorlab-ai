<?php
// This security check runs on the server before the page loads.
session_start();
if (!isset($_SESSION['sales_user_id'])) {
    header('Location: sales_dashboard.php'); // Redirect to dashboard if not logged in
    exit();
}
$sales_username = $_SESSION['sales_user_username'];
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Art Request | Sales Portal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; background-color: #111827; color: #f9fafb; }
        .form-input { background-color: #374151; border-color: #4b5563; }
        .btn-primary { background-color: #2563eb; }
        .btn-primary:hover { background-color: #1d4ed8; }
    </style>
</head>
<body class="antialiased p-8">
    <div class="max-w-3xl mx-auto">
        <div class="flex justify-between items-center mb-6">
            <div>
                 <h1 class="text-3xl font-bold">New Art Request</h1>
                 <p class="text-gray-400">Logged in as: <strong class="text-white"><?php echo htmlspecialchars($sales_username); ?></strong></p>
            </div>
             <!-- **THE FIX IS HERE**: The link now correctly points back to the sales dashboard. -->
             <a href="sales_dashboard.php" class="text-sm text-blue-400 hover:text-blue-300">&larr; Back to Dashboard</a>
        </div>
        <form id="art-request-form" class="bg-[#1f2937] p-8 rounded-lg border border-gray-700 space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div><label for="customer_name" class="block text-sm font-medium mb-1">Customer Name</label><input type="text" id="customer_name" name="customer_name" required class="w-full p-2 rounded-md form-input"></div>
                <div><label for="po_number" class="block text-sm font-medium mb-1">PO Number (Optional)</label><input type="text" id="po_number" name="po_number" class="w-full p-2 rounded-md form-input"></div>
                <div><label for="due_date" class="block text-sm font-medium mb-1">Due Date</label><input type="date" id="due_date" name="due_date" required class="w-full p-2 rounded-md form-input"></div>
                <div><label for="product_type" class="block text-sm font-medium mb-1">Garment / Product Type</label><select id="product_type" name="product_type" required class="w-full p-2 rounded-md form-input"><option>T-Shirt</option><option>Hoodie</option><option>Hat</option><option>Polo</option><option>Other</option></select></div>
                <div><label for="image_placement" class="block text-sm font-medium mb-1">Image Placement</label><select id="image_placement" name="image_placement" required class="w-full p-2 rounded-md form-input"><option>Full Front</option><option>Left Chest</option><option>Full Back</option><option>Sleeve</option><option>Other</option></select></div>
                <div><label for="process_type" class="block text-sm font-medium mb-1">Process Type</label><select id="process_type" name="process_type" required class="w-full p-2 rounded-md form-input"><option>Screenprinting</option><option>DTF</option><option>Embroidery</option></select></div>
            </div>
            <div><label for="request_type" class="block text-sm font-medium mb-1">Request Type</label><select id="request_type" name="request_type" required class="w-full p-2 rounded-md form-input"><option>New Design</option><option>Mock Up</option><option>Color Separation</option><option>Vectorization</option></select></div>
            <div><label for="details" class="block text-sm font-medium mb-1">Details & Instructions</label><textarea id="details" name="details" rows="4" required class="w-full p-2 rounded-md form-input"></textarea></div>
            <div>
                 <label for="artwork_file" class="block text-sm font-medium mb-1">Artwork File (Optional)</label>
                 <!-- **THE FIX IS HERE**: The 'required' attribute has been removed. -->
                 <input type="file" id="artwork_file" name="artwork_file" class="w-full text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-gray-600 file:text-white hover:file:bg-gray-500">
            </div>
            <div><button type="submit" class="w-full py-3 px-4 rounded-md text-white font-semibold btn-primary">Submit Request</button></div>
        </form>
        <div id="message" class="mt-4 text-center"></div>
    </div>
    <script>
        document.getElementById('art-request-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            const messageEl = document.getElementById('message');
            const submitButton = this.querySelector('button');
            messageEl.textContent = ''; submitButton.disabled = true; submitButton.textContent = 'Submitting...';
            const formData = new FormData(this);
            try {
                const response = await fetch('sales_api.php?action=submit_request', { method: 'POST', body: formData });
                const result = await response.json();
                if (result.status === 'success') {
                    messageEl.className = 'text-green-400';
                    messageEl.textContent = 'Request submitted successfully!';
                    this.reset();
                } else { throw new Error(result.message); }
            } catch (error) {
                messageEl.className = 'text-red-400';
                messageEl.textContent = `Error: ${error.message}`;
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = 'Submit Request';
            }
        });
    </script>
</body>
</html>

