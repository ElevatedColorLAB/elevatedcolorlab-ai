<?php
session_start();
if (!isset($_SESSION['sales_user_id'])) {
    header('Location: sales_login.html');
    exit();
}
$sales_username = $_SESSION['sales_user_username'];
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sales Dashboard | ElevatedColorLab</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; background-color: #111827; color: #f9fafb; }
        .card { background-color: #1f2937; border: 1px solid #374151; border-radius: 0.75rem; }
        .btn { display: inline-flex; align-items: center; justify-content: center; padding: 0.6rem 1.2rem; border-radius: 0.5rem; font-weight: 600; transition: all 0.2s ease; cursor: pointer; border: 1px solid transparent; }
        .btn-primary { background-color: #2563eb; color: white; }
        .btn-primary:hover { background-color: #1d4ed8; }
        .btn-secondary { background-color: #374151; color: white; }
        .btn-secondary:hover { background-color: #4b5563; }
        .loader { width: 30px; height: 30px; border-radius: 50%; border: 4px solid #374151; border-top-color: #2563eb; animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .modal-overlay { position: fixed; inset: 0; background-color: rgba(0,0,0,0.7); backdrop-filter: blur(4px); z-index: 10000; display: none; align-items: center; justify-content: center; }
        .conversation-bubble { padding: 0.75rem 1rem; border-radius: 0.75rem; }
        .conversation-bubble.sales { background-color: #374151; }
        .conversation-bubble.art { background-color: #2563eb; }
    </style>
</head>
<body class="antialiased">
    <div class="min-h-screen flex">
        <aside class="w-64 bg-[#1f2937] p-6 flex-shrink-0 flex flex-col">
            <div class="flex items-center space-x-3 mb-10">
                <div class="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center">
                    <i class="fas fa-layer-group text-white"></i>
                </div>
                <span class="text-xl font-bold tracking-tight text-white">Elevated<span class="text-blue-500">ColorLab</span></span>
            </div>
            <nav class="space-y-2 flex-grow">
                <a href="sales_dashboard.php" class="flex items-center space-x-3 text-white bg-blue-600/20 border-l-2 border-blue-500 py-2 px-4 rounded-r-md">
                    <i class="fas fa-tachometer-alt fa-fw text-blue-400"></i>
                    <span class="font-semibold">My Requests</span>
                </a>
                <a href="new_sales_request.php" class="flex items-center space-x-3 text-gray-400 hover:text-white hover:bg-gray-700/50 py-2 px-4 rounded-md">
                    <i class="fas fa-plus fa-fw"></i>
                    <span>New Request</span>
                </a>
            </nav>
            <div class="border-t border-gray-700 pt-4 mt-4">
                 <p class="px-4 text-xs text-gray-500 uppercase font-semibold">Logged In As</p>
                 <p class="px-4 py-2 text-white font-semibold"><?php echo htmlspecialchars($sales_username); ?></p>
                 <a href="sales_auth.php?action=logout" class="flex items-center space-x-3 text-gray-400 hover:text-white hover:bg-gray-700/50 py-2 px-4 rounded-md mt-2">
                    <i class="fas fa-sign-out-alt fa-fw"></i>
                    <span>Logout</span>
                </a>
            </div>
        </aside>

        <main class="flex-1 p-8 lg:p-12">
            <h1 class="text-4xl font-bold text-white mb-2">My Art Requests</h1>
            <p class="text-gray-400 mb-8">Track the status of your submitted jobs.</p>
            <div class="card p-6">
                <div class="overflow-x-auto">
                    <table class="w-full text-sm text-left text-gray-400">
                        <thead class="text-xs bg-gray-800 text-gray-300 uppercase">
                            <tr>
                                <th scope="col" class="px-4 py-3">Customer</th>
                                <th scope="col" class="px-4 py-3">Request / PO</th>
                                <th scope="col" class="px-4 py-3">Date Submitted</th>
                                <th scope="col" class="px-4 py-3">Status</th>
                                <th scope="col" class="px-4 py-3 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="sales-requests-tbody"></tbody>
                    </table>
                </div>
            </div>
        </main>
    </div>

    <div id="sales-modal" class="modal-overlay">
        <div class="card w-full max-w-2xl max-h-[90vh] flex flex-col">
            <div class="p-6 border-b border-slate-700 flex justify-between items-center">
                <h3 id="sales-modal-title" class="text-xl font-bold">Communication Log</h3>
                <button onclick="closeModal('sales-modal')" class="text-gray-400 hover:text-white">&times;</button>
            </div>
            <div class="p-6 overflow-y-auto flex-grow">
                <div id="sales-conversation-log" class="space-y-4 max-h-96 overflow-y-auto pr-2"></div>
            </div>
            <div class="p-6 border-t border-slate-700">
                <form id="sales-response-form" class="flex items-center space-x-3">
                    <input type="text" id="sales-response-message" placeholder="Type your message..." class="w-full bg-slate-800 border border-slate-600 rounded-md p-2 text-sm">
                    <button type="submit" class="btn btn-primary">Send</button>
                </form>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const tbody = document.getElementById('sales-requests-tbody');
            const modalTitle = document.getElementById('sales-modal-title');
            const convoLog = document.getElementById('sales-conversation-log');
            const responseForm = document.getElementById('sales-response-form');
            const responseInput = document.getElementById('sales-response-message');
            let currentRequestId = null;
            async function fetchSalesRequests() {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center p-8"><div class="loader mx-auto"></div></td></tr>`;
                try {
                    const response = await fetch('sales_api.php?action=get_my_requests');
                    const result = await response.json();
                    if (result.status !== 'success') throw new Error(result.message);
                    populateTable(result.data);
                } catch (error) {
                    tbody.innerHTML = `<tr><td colspan="5" class="text-center p-8 text-red-400">Error: ${error.message}</td></tr>`;
                }
            }
            function populateTable(requests) {
                tbody.innerHTML = '';
                if(requests.length === 0){
                    tbody.innerHTML = `<tr><td colspan="5" class="text-center p-8 text-gray-500">You haven't submitted any requests yet.</td></tr>`;
                    return;
                }
                const statusColors = {'New':'bg-blue-900 text-blue-300','In Progress':'bg-yellow-900 text-yellow-300','Needs Revision':'bg-red-900 text-red-300','Approved':'bg-purple-900 text-purple-300','Complete':'bg-green-900 text-green-300'};
                requests.forEach(req => {
                    const row = document.createElement('tr');
                    row.className = 'border-b border-gray-700 hover:bg-gray-800';
                    row.innerHTML = `<td class="px-4 py-3 font-medium">${escapeHtml(req.customer_name)}</td><td class="px-4 py-3">${escapeHtml(req.po_number ? `${req.request_type} (PO: ${req.po_number})` : req.request_type)}</td><td class="px-4 py-3">${new Date(req.created_at).toLocaleDateString()}</td><td class="px-4 py-3"><span class="${statusColors[req.status] || ''} text-xs px-2 py-1 rounded-full">${escapeHtml(req.status)}</span></td><td class="px-4 py-3 text-right"><button class="btn btn-secondary text-xs" data-id="${req.id}" data-customer="${req.customer_name}"><i class="fas fa-comments mr-2"></i> View & Respond</button></td>`;
                    tbody.appendChild(row);
                });
            }
            tbody.addEventListener('click', async e => {
                const button = e.target.closest('button');
                if(button && button.dataset.id) {
                    currentRequestId = button.dataset.id;
                    modalTitle.textContent = `Conversation for ${button.dataset.customer}`;
                    openModal('sales-modal');
                    convoLog.innerHTML = `<div class="loader mx-auto"></div>`;
                    try {
                        const response = await fetch(`sales_api.php?action=get_request&id=${currentRequestId}`);
                        const result = await response.json();
                        if (result.status !== 'success') throw new Error(result.message);
                        renderConversation(result.data.conversation);
                    } catch (error) {
                        convoLog.innerHTML = `<p class="text-red-400">Could not load conversation.</p>`;
                    }
                }
            });
            responseForm.addEventListener('submit', async e => {
                e.preventDefault();
                const message = responseInput.value.trim();
                if (!message || !currentRequestId) return;
                try {
                    const response = await fetch(`sales_api.php?action=add_message`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ request_id: currentRequestId, message: message })
                    });
                    const result = await response.json();
                    if (result.status !== 'success') throw new Error(result.message);
                    responseInput.value = '';
                    renderConversation(result.data.conversation);
                } catch (error) {
                    alert(`Error sending message: ${error.message}`);
                }
            });
            function renderConversation(conversation) {
                convoLog.innerHTML = '';
                if (!conversation || conversation.length === 0) {
                    convoLog.innerHTML = '<p class="text-gray-500 text-center">No messages yet.</p>'; return;
                }
                conversation.forEach(msg => {
                    const isArtDept = msg.author_name === 'Art Department';
                    convoLog.innerHTML += `<div class="flex flex-col ${isArtDept ? 'items-start' : 'items-end'}"><div class="w-full md:w-5/6"><div class="flex justify-between items-baseline mb-1 px-1"><p class="font-bold text-sm">${escapeHtml(msg.author_name)}</p><p class="text-xs text-gray-500">${new Date(msg.created_at).toLocaleString([], {dateStyle: 'short', timeStyle: 'short'})}</p></div><div class="conversation-bubble ${isArtDept ? 'art' : 'sales'}"><p>${escapeHtml(msg.message)}</p></div></div></div>`;
                });
                convoLog.scrollTop = convoLog.scrollHeight;
            }
            window.openModal = (id) => document.getElementById(id).style.display = 'flex';
            window.closeModal = (id) => document.getElementById(id).style.display = 'none';
            function escapeHtml(str) { return str ? str.toString().replace(/[&<>"']/g, m => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#039;' }[m])) : ''; }
            fetchSalesRequests();
        });
    </script>
</body>
</html>
