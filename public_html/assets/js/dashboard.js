document.addEventListener('DOMContentLoaded', () => {
    const username = sessionStorage.getItem('main_user_username');
    const token = sessionStorage.getItem('main_user_token');
    const role = sessionStorage.getItem('main_user_role');

    if (!token || !username) {
        window.location.href = 'login.html';
        return;
    }

    document.getElementById('welcome-user').textContent = username;

    // Logout
    document.getElementById('logout-button').addEventListener('click', () => {
        sessionStorage.clear();
        window.location.href = 'login.html';
    });

    // Role-based visibility
    const betaApprovalsLink = document.getElementById('beta-approvals-link');
    if (role !== 'admin' && role !== 'overseer') {
        betaApprovalsLink.style.display = 'none';
    }

    // Art request polling
    async function checkForNewArtRequests() {
        try {
            const response = await fetch('/sales_api.php?action=get_requests');
            if (!response.ok) return;

            const result = await response.json();
            if (result.status === 'success') {
                const hasNew = result.data.some(req => req.status === 'New');
                const card = document.getElementById('art-requests-card');

                if (hasNew) card.classList.add('new-request-pulse');
                else card.classList.remove('new-request-pulse');
            }
        } catch (error) {
            console.error("Could not check for new art requests:", error);
        }
    }

    checkForNewArtRequests();
    setInterval(checkForNewArtRequests, 15000);
});