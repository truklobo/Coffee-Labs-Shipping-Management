// --- Create Shipping Page Logic ---
window.addEventListener('DOMContentLoaded', function() {
	if (document.getElementById('shippingForm')) {
		// Set default dates
		const today = new Date();
		document.getElementById('orderDate').valueAsDate = today;
		const futureDate = new Date();
		futureDate.setDate(today.getDate() + 7);
		document.getElementById('expectedDelivery').valueAsDate = futureDate;

		// Reset form
		window.resetForm = function() {
			if (confirm('Are you sure you want to cancel? All entered data will be lost.')) {
				document.getElementById('shippingForm').reset();
				document.getElementById('orderDate').valueAsDate = new Date();
				const future = new Date();
				future.setDate(future.getDate() + 7);
				document.getElementById('expectedDelivery').valueAsDate = future;
			}
		}

		// Close confirmation
		window.closeConfirmation = function() {
			document.getElementById('confirmationOverlay').classList.remove('show');
			document.getElementById('shippingForm').reset();
			document.getElementById('orderDate').valueAsDate = new Date();
			const future = new Date();
			future.setDate(future.getDate() + 7);
			document.getElementById('expectedDelivery').valueAsDate = future;
		}

		// Form submission
		document.getElementById('shippingForm').addEventListener('submit', function(e) {
			e.preventDefault();
			
			// Validate required fields
			const supplierName = document.getElementById('supplierName').value.trim();
			const orderDate = document.getElementById('orderDate').value.trim();
			const trackingNumber = document.getElementById('trackingNumber').value.trim();
			const itemName = document.getElementById('itemName').value.trim();
			const orderQuantity = document.getElementById('orderQuantity').value.trim();
			const orderTotal = document.getElementById('orderTotal').value.trim();
			
			if (!supplierName || !orderDate || !trackingNumber || !itemName || !orderQuantity || !orderTotal) {
			alert('Please fill in all required fields marked with *');
			return;
		}
		
		// Prepare form data
		const formData = new FormData();
		formData.append('supplier_name', supplierName);
		formData.append('order_date', orderDate);
		formData.append('exp_delivery_date', document.getElementById('expectedDelivery').value.trim());
		formData.append('actual_delivery_date', document.getElementById('actualDelivery').value.trim());
		formData.append('tracking_number', trackingNumber);
		formData.append('shipping_carrier', document.getElementById('shippingCarrier').value);
		formData.append('item_name', itemName);
		formData.append('quantity', orderQuantity);
		formData.append('order_total', orderTotal);
		formData.append('notes', document.getElementById('orderNotes').value.trim());			// Submit to backend
			fetch('/createshipping', {
				method: 'POST',
				body: formData
			})
			.then(response => response.json())
			.then(data => {
				if (data.success) {
					document.getElementById('confirmationOverlay').classList.add('show');
					document.getElementById('confirmationDetails').innerHTML = 
						`<p><strong>Shipping ID:</strong> ${data.shipping_id}</p>
						 <p><strong>Supplier:</strong> ${supplierName}</p>
						 <p><strong>Item:</strong> ${itemName}</p>`;
				} else {
					alert('Error: ' + (data.errors ? data.errors.join(', ') : 'Unknown error'));
				}
			})
			.catch(error => {
				console.error('Error:', error);
				alert('Failed to create shipping record. Please try again.');
			});
		});
	}
});

// --- Modify Shipping Page Logic ---
window.addEventListener('DOMContentLoaded', function() {
	if (document.getElementById('searchOrderId')) {

		window.showAlert = function(message, type) {
			const alertBox = document.getElementById('alertBox');
			alertBox.className = 'alert alert-' + type + ' show';
			alertBox.textContent = message;
			setTimeout(() => {
				alertBox.classList.remove('show');
			}, 5000);
		}

		window.searchOrder = function() {
			const orderId = document.getElementById('searchOrderId').value.trim();
			if (!orderId) {
				showAlert('Please enter an Order ID', 'error');
				return;
			}
			
			// Use fetch to search for order
			fetch(`/searchorder?shipping_id=${encodeURIComponent(orderId)}`)
				.then(response => response.text())
				.then(data => {
					document.getElementById('searchResultsContainer').innerHTML = data;
					document.getElementById('detailsSection').classList.add('show');
					showAlert('Search complete! Click on a row to edit.', 'success');
					
					// Add click handlers to table rows
					const rows = document.querySelectorAll('.clickable-row');
					rows.forEach(row => {
						row.addEventListener('click', function() {
							const shippingId = this.dataset.shippingId;
							const supplierName = this.dataset.supplierName;
							const orderDate = this.dataset.orderDate;
							const expDelivery = this.dataset.expDelivery;
							const actualDelivery = this.dataset.actualDelivery;
							const tracking = this.dataset.tracking;
							const carrier = this.dataset.carrier;
							const itemName = this.dataset.item;
							const quantity = this.dataset.quantity;
							const total = this.dataset.total;
							const notes = this.dataset.notes;
							
							selectOrderForEdit(shippingId, supplierName, orderDate, expDelivery, actualDelivery, tracking, carrier, itemName, quantity, total, notes);
						});
					});
				})
				.catch(error => {
					console.error('Error:', error);
					showAlert('Error searching for order. Please try again.', 'error');
				});
		}

		window.selectOrderForEdit = function(shippingId, supplierName, orderDate, expDelivery, actualDelivery, tracking, carrier, itemName, quantity, total, notes) {
			// Populate form fields
			document.getElementById('hiddenShippingId').value = shippingId;
			document.getElementById('hiddenSupplierName').value = supplierName;
			document.getElementById('hiddenOrderDate').value = orderDate;
			document.getElementById('displayOrderId').textContent = shippingId;
			document.getElementById('displaySupplier').textContent = supplierName;
			document.getElementById('updateDeliveryDate').value = expDelivery;
			document.getElementById('actualDeliveryDate').value = actualDelivery;
			document.getElementById('updateTracking').value = tracking;
			document.getElementById('updateCarrier').value = carrier;
			document.getElementById('updateItemName').value = itemName;
			document.getElementById('updateQuantity').value = quantity;
			document.getElementById('updateTotal').value = total;
			document.getElementById('updateNotes').value = notes === 'N/A' ? '' : notes;
			
			// Show modify form
			document.getElementById('modifyFormSection').style.display = 'block';
			document.getElementById('modifyFormSection').scrollIntoView({ behavior: 'smooth' });
		}

		window.cancelEdit = function() {
			document.getElementById('modifyFormSection').style.display = 'none';
			document.getElementById('modifyForm').reset();
		}

		window.clearSearch = function() {
			document.getElementById('searchOrderId').value = '';
			document.getElementById('detailsSection').classList.remove('show');
			document.getElementById('searchResultsContainer').innerHTML = '';
			document.getElementById('modifyFormSection').style.display = 'none';
			const alertBox = document.getElementById('alertBox');
			alertBox.classList.remove('show');
			// Clear the form as well
			document.getElementById('modifyForm').reset();
		}

		window.cancelModify = function() {
			clearSearch();
		}

		// Form submission
		document.getElementById('modifyForm').addEventListener('submit', function(e) {
			e.preventDefault();
			
			const formData = new FormData();
			formData.append('shipping_id', document.getElementById('hiddenShippingId').value);
			formData.append('supplier_name', document.getElementById('hiddenSupplierName').value);
			formData.append('order_date', document.getElementById('hiddenOrderDate').value);
			formData.append('exp_delivery_date', document.getElementById('updateDeliveryDate').value);
			formData.append('actual_delivery_date', document.getElementById('actualDeliveryDate').value);
			formData.append('tracking_number', document.getElementById('updateTracking').value);
			formData.append('shipping_carrier', document.getElementById('updateCarrier').value);
			formData.append('item_name', document.getElementById('updateItemName').value);
			formData.append('quantity', document.getElementById('updateQuantity').value);
			formData.append('order_total', document.getElementById('updateTotal').value);
			formData.append('notes', document.getElementById('updateNotes').value);
			
			fetch('/updateshipping', {
				method: 'POST',
				body: formData
			})
			.then(response => response.json())
			.then(data => {
				if (data.success) {
					// Show success message
					const alertBox = document.getElementById('alertBox');
					alertBox.textContent = '✓ Order modified successfully! All changes have been saved.';
					alertBox.className = 'alert alert-success show';
					alertBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
					
					// Hide the form
					document.getElementById('modifyFormSection').style.display = 'none';
					
					// Refresh the search results to show updated data
					searchOrder();
					
					// Auto-hide success message after 5 seconds
					setTimeout(() => {
						alertBox.classList.remove('show');
					}, 5000);
				} else {
					const alertBox = document.getElementById('alertBox');
					alertBox.textContent = '✗ Error: ' + (data.error || 'Unknown error');
					alertBox.className = 'alert alert-error show';
					alertBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
				}
			})
			.catch(error => {
				console.error('Error:', error);
				const alertBox = document.getElementById('alertBox');
				alertBox.textContent = '✗ Failed to update order. Please try again.';
				alertBox.className = 'alert alert-error show';
				alertBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
			});
		});
	}
});

// --- Search Shipping Page Logic --- 
window.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('filterOrderId') || document.getElementById('filterSupplier')) {
        
        window.searchOrders = function() {
            const shippingId = document.getElementById('filterOrderId').value.trim();
            const supplierName = document.getElementById('filterSupplier').value.trim();
            const shippingCarrier = document.getElementById('filterCarrier').value;
            const sortByDate = document.getElementById('sortByDate').value;
            const sortByItem = document.getElementById('sortByItem').value;
            const sortByTotal = document.getElementById('sortByTotal').value;
            
            // Build query parameters
            const params = new URLSearchParams();
            if (shippingId) params.append('shipping_id', shippingId);
            if (supplierName) params.append('supplier_name', supplierName);
            if (shippingCarrier) params.append('shipping_carrier', shippingCarrier);
            if (sortByDate) params.append('sort_date', sortByDate);
            if (sortByItem) params.append('sort_item', sortByItem);
            if (sortByTotal) params.append('sort_total', sortByTotal);
            
            // Use fetch to make AJAX request
            fetch(`/searchorders?${params.toString()}`)
                .then(response => response.text())
                .then(data => {
                    console.log(data);
                    document.getElementById('resultsTableContainer').innerHTML = data;
                    // Update result count if needed
                    const rows = document.querySelectorAll('#resultsTableContainer table tbody tr');
                    document.getElementById('resultCount').textContent = rows.length;
                })
                .catch(error => {
                    console.error('Error:', error);
                    document.getElementById('resultsTableContainer').innerHTML = 
                        '<p style="text-align: center; color: #FC8181; padding: 20px;">Error loading results. Please try again.</p>';
                });
        }
        
        window.clearFilters = function() {
            document.getElementById('filterOrderId').value = '';
            document.getElementById('filterSupplier').value = '';
            document.getElementById('filterCarrier').value = '';
            document.getElementById('sortByDate').value = '';
            document.getElementById('sortByItem').value = '';
            document.getElementById('sortByTotal').value = '';
            document.getElementById('resultsTableContainer').innerHTML = '';
            document.getElementById('resultCount').textContent = '0';
        }
    }
});

// --- Delete Shipping Page Logic ---
window.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('sortBy') && document.getElementById('recordsTableContainer')) {
        
        window.showAlert = function(message, type) {
            const alertBox = document.getElementById('alertBox');
            alertBox.className = 'alert alert-' + type + ' show';
            alertBox.textContent = message;
            setTimeout(() => {
                alertBox.classList.remove('show');
            }, 5000);
        }
        
        window.loadRecords = function() {
            const sortBy = document.getElementById('sortBy').value;
            const carrier = document.getElementById('filterCarrier').value;
            
            // Build query parameters
            const params = new URLSearchParams();
            params.append('sort_by', sortBy);
            if (carrier) params.append('carrier', carrier);
            
            // Use fetch to load all records
            fetch(`/getallrecords?${params.toString()}`)
                .then(response => response.text())
                .then(data => {
                    document.getElementById('recordsTableContainer').innerHTML = data;
                    
                    // Add click handlers to table rows
                    const rows = document.querySelectorAll('.clickable-row');
                    rows.forEach(row => {
                        row.addEventListener('click', function() {
                            const shippingId = this.dataset.shippingId;
                            const supplierName = this.dataset.supplierName;
                            
                            if (confirm(`Are you sure you want to delete record #${shippingId} (${supplierName})?\n\nThis action cannot be undone.`)) {
                                deleteRecord(shippingId);
                            }
                        });
                    });
                })
                .catch(error => {
                    console.error('Error:', error);
                    showAlert('Error loading records. Please try again.', 'error');
                });
        }
        
        window.deleteRecord = function(shippingId) {
            fetch('/deleterecord', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    shipping_id: shippingId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('Record deleted successfully!', 'success');
                    // Reload the records
                    loadRecords();
                } else {
                    showAlert('Error: ' + (data.errors ? data.errors.join(', ') : 'Unknown error'), 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('Failed to delete record. Please try again.', 'error');
            });
        }
        
        // Load records on page load
        loadRecords();
    }
});
