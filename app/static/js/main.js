// app/static/js/main.js
$(document).ready(function() {
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
    
    // Confirm dangerous actions
    $('.confirm-action').click(function(e) {
        if (!confirm('Are you sure you want to perform this action?')) {
            e.preventDefault();
        }
    });
    
    // Grade input validation
    $('input[type="number"]').on('change', function() {
        var min = parseFloat($(this).attr('min'));
        var max = parseFloat($(this).attr('max'));
        var val = parseFloat($(this).val());
        
        if (!isNaN(val)) {
            if (!isNaN(min) && val < min) $(this).val(min);
            if (!isNaN(max) && val > max) $(this).val(max);
        }
    });
    
    // Calculate overall grade dynamically
    $('.grade-input').on('input', function() {
        var sectionId = $(this).data('section-id');
        // AJAX call to recalculate grades
        $.ajax({
            url: '/api/recalculate-grades/' + sectionId,
            method: 'POST',
            success: function(response) {
                if (response.success) {
                    location.reload();
                }
            }
        });
    });
    
    // Tooltips
    $('[data-toggle="tooltip"]').tooltip();
});