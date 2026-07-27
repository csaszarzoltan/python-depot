// Vulnerability Dashboard — client-side enhancements

document.addEventListener('DOMContentLoaded', function() {
    // Hamburger menu toggle
    const hamburger = document.getElementById('hamburger-btn');
    const sidebar = document.querySelector('.sidebar');
    if (hamburger && sidebar) {
        hamburger.addEventListener('click', function() {
            sidebar.style.display = sidebar.style.display === 'block' ? 'none' : 'block';
        });
    }

    // Package search filter
    const searchInput = document.getElementById('package-search');
    if (searchInput) {
        searchInput.addEventListener('keyup', function() {
            const query = this.value.toLowerCase();
            const rows = document.querySelectorAll('.packages-table tbody tr');
            rows.forEach(function(row) {
                const name = row.cells[0].textContent.toLowerCase();
                row.style.display = name.includes(query) ? '' : 'none';
            });
        });
    }

    // Severity filter
    const severityFilter = document.getElementById('severity-filter');
    if (severityFilter) {
        severityFilter.addEventListener('change', function() {
            const severity = this.value;
            if (severity) {
                window.location.href = '/dashboard/alerts?severity=' + severity;
            } else {
                window.location.href = '/dashboard/alerts';
            }
        });
    }
});
