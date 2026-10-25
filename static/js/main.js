// Quarry Management System - Interactive Logic & Pass Auto-population

document.addEventListener('DOMContentLoaded', function() {
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Driver Pass Creation Form Dynamic Behavior
    const orderSelect = document.getElementById('order_id');
    const driverSelect = document.getElementById('driver_id');
    const validUntilInput = document.getElementById('valid_until');
    const issueDateInput = document.getElementById('issue_date');
    const passForm = document.getElementById('createPassForm');

    if (orderSelect) {
        orderSelect.addEventListener('change', function() {
            const orderId = this.value;
            if (!orderId) {
                clearOrderFields();
                return;
            }

            fetch(`/dealer/api/order_info/${orderId}`)
                .then(response => {
                    if (!response.ok) throw new Error('Order data fetch failed');
                    return response.json();
                })
                .then(data => {
                    document.getElementById('client_name').value = data.client_name || '';
                    document.getElementById('material').value = data.material_name || '';
                    document.getElementById('quantity').value = `${data.quantity} ${data.unit || 'Ton'}`;
                    document.getElementById('delivery_address').value = data.delivery_address || '';

                    // If order has an allocated driver, select it automatically
                    if (data.driver && driverSelect) {
                        driverSelect.value = data.driver.driver_id;
                        document.getElementById('vehicle_number').value = data.driver.vehicle_number || '';
                    }
                })
                .catch(err => {
                    console.error('Error loading order details:', err);
                });
        });
    }

    if (driverSelect) {
        driverSelect.addEventListener('change', function() {
            const driverId = this.value;
            if (!driverId) {
                document.getElementById('vehicle_number').value = '';
                return;
            }

            fetch(`/dealer/api/driver_info/${driverId}`)
                .then(response => {
                    if (!response.ok) throw new Error('Driver data fetch failed');
                    return response.json();
                })
                .then(data => {
                    document.getElementById('vehicle_number').value = data.vehicle_number || '';
                })
                .catch(err => {
                    console.error('Error loading driver details:', err);
                });
        });
    }

    if (passForm) {
        passForm.addEventListener('submit', function(e) {
            if (issueDateInput && validUntilInput) {
                const issueDate = new Date(issueDateInput.value);
                const validUntil = new Date(validUntilInput.value);

                if (validUntil < issueDate) {
                    e.preventDefault();
                    alert('Error: "Valid Until" date cannot be earlier than the "Issue Date".');
                    validUntilInput.focus();
                }
            }
        });
    }

    function clearOrderFields() {
        const fields = ['client_name', 'material', 'quantity', 'delivery_address', 'vehicle_number'];
        fields.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
    }
});
