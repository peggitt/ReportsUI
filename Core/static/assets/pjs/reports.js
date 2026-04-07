/**
 * Report actions functionality
 * Handles report action operations like view, edit, delete
 */

// Function to handle report actions
function ActionUser(reportId) {
    // View report action
    console.log("Viewing report with ID:", reportId);
    
    window.location.href = "/reports/" + reportId;
    // Show an alert for testing purposes
    //alert("Viewing report with ID: " + reportId);
    
    // Redirect or perform AJAX call to view the report
    // Example implementation (commented out for testing):
    // window.location.href = `/reports/view/${reportId}`;
}

// Initialize any Bootstrap components when document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Completely disable DataTables initialization to avoid conflicts
    // We'll just rely on the standard HTML table
    
    // Verify that dropdown buttons are properly configured
    console.log("Dropdown buttons found: " + $('.dropdown-toggle').length);
    
    // No need to initialize dropdowns in Bootstrap 5 as they work automatically
    // with data-bs-toggle="dropdown" attribute
});


document.addEventListener('DOMContentLoaded', function () {
    const groupRows = document.querySelectorAll('.group-row');
    groupRows.forEach(row => {
        row.addEventListener('click', function () {
            const icon = this.querySelector('i');
            if (icon.classList.contains('fa-chevron-right')) {
                icon.classList.replace('fa-chevron-right', 'fa-chevron-down');
            } else {
                icon.classList.replace('fa-chevron-down', 'fa-chevron-right');
            }
        });
    });
});